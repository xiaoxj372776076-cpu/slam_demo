#!/usr/bin/env python3
"""Run ORB-SLAM3 on TUM RGB-D fr1/xyz and generate a visual report."""

from __future__ import annotations

import argparse
import bisect
import csv
import html
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent


def read_index(path: Path) -> list[tuple[float, str]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split()
            rows.append((float(parts[0]), parts[1]))
    if not rows:
        raise ValueError(f"No timestamps in {path}")
    return rows


def make_associations(dataset: Path, output: Path, max_gap: float = 0.02) -> list[tuple[float, str]]:
    rgbs = read_index(dataset / "rgb.txt")
    depths = read_index(dataset / "depth.txt")
    times = [row[0] for row in depths]
    pairs = []
    with output.open("w", encoding="utf-8") as handle:
        for rgb_time, rgb_path in rgbs:
            index = bisect.bisect_left(times, rgb_time)
            candidates = [i for i in (index - 1, index) if 0 <= i < len(depths)]
            nearest = min(candidates, key=lambda i: abs(times[i] - rgb_time))
            depth_time, depth_path = depths[nearest]
            if abs(depth_time - rgb_time) <= max_gap:
                handle.write(f"{rgb_time:.9f} {rgb_path} {depth_time:.9f} {depth_path}\n")
                pairs.append((rgb_time, rgb_path))
    if len(pairs) < 20:
        raise ValueError(f"Only {len(pairs)} synchronized RGB-D pairs found")
    return pairs


def read_tum_trajectory(path: Path) -> np.ndarray:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"ORB-SLAM3 did not produce a trajectory: {path}")
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            values = [float(value) for value in line.split()]
            if len(values) != 8:
                raise ValueError(f"Expected TUM trajectory format in {path}")
            rows.append(values)
    if not rows:
        raise RuntimeError("ORB-SLAM3 saved no tracked poses")
    return np.asarray(rows)


def match_ground_truth(trajectory: np.ndarray, path: Path, tolerance: float = 0.02):
    if not path.exists():
        return None
    truth = read_tum_trajectory(path)
    truth_times = truth[:, 0].tolist()
    estimates, references = [], []
    for row in trajectory:
        index = bisect.bisect_left(truth_times, row[0])
        candidates = [i for i in (index - 1, index) if 0 <= i < len(truth)]
        nearest = min(candidates, key=lambda i: abs(truth_times[i] - row[0]))
        if abs(truth_times[nearest] - row[0]) <= tolerance:
            estimates.append(row[1:4])
            references.append(truth[nearest, 1:4])
    if len(estimates) < 3:
        return None
    return np.asarray(estimates), np.asarray(references)


def rigid_align(estimated: np.ndarray, truth: np.ndarray):
    """SE(3) alignment only: RGB-D scale remains fixed at 1."""
    source_mean = estimated.mean(axis=0)
    target_mean = truth.mean(axis=0)
    U, _, Vt = np.linalg.svd((estimated - source_mean).T @ (truth - target_mean))
    D = np.diag([1.0, 1.0, np.linalg.det(U @ Vt)])
    rotation = U @ D @ Vt
    aligned = (estimated - source_mean) @ rotation + target_mean
    return aligned, rotation, target_mean - source_mean @ rotation


def plot_trajectory(trajectory: np.ndarray, ground_truth: Path, output: Path) -> dict:
    est = trajectory[:, 1:4]
    comparison = match_ground_truth(trajectory, ground_truth)
    metrics = {"trajectory_poses": len(trajectory), "ate_rmse_m": None}
    aligned = est
    if comparison is not None:
        paired_est, paired_truth = comparison
        aligned_paired, rotation, translation = rigid_align(paired_est, paired_truth)
        aligned = est @ rotation + translation
        metrics["ate_rmse_m"] = float(np.sqrt(np.mean(np.sum((aligned_paired - paired_truth) ** 2, axis=1))))
        metrics["matched_ground_truth_poses"] = len(paired_est)

    figure, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for ax, first, second, title in (
        (axes[0], 0, 2, "Top view (X-Z)"),
        (axes[1], 0, 1, "Front view (X-Y)"),
    ):
        if comparison is not None:
            ax.plot(paired_truth[:, first], paired_truth[:, second], color="0.55", lw=2, label="TUM ground truth")
        ax.plot(aligned[:, first], aligned[:, second], color="#d24b39", lw=1.6, label="ORB-SLAM3")
        ax.scatter(aligned[0, first], aligned[0, second], c="#157f52", s=45, zorder=3, label="Start")
        ax.set(xlabel="metres", ylabel="metres", title=title)
        ax.grid(alpha=0.25)
        ax.axis("equal")
        ax.legend(loc="best", fontsize=8)
    figure.suptitle("TUM fr1/xyz — RGB-D camera trajectory (SE(3)-aligned for comparison)")
    figure.savefig(output, dpi=170)
    plt.close(figure)
    return metrics


def draw_orb_matches(dataset: Path, frames: list[tuple[float, str]], index: int,
                     output: Path) -> dict:
    gap = 8
    second = min(index + gap, len(frames) - 1)
    images = [cv2.imread(str(dataset / frames[i][1]), cv2.IMREAD_COLOR) for i in (index, second)]
    if any(image is None for image in images):
        raise RuntimeError(f"Cannot read RGB images at {index} and {second}")
    gray = [cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) for image in images]
    orb = cv2.ORB_create(nfeatures=1600)
    keypoints, descriptors = [], []
    for image in gray:
        points, desc = orb.detectAndCompute(image, None)
        keypoints.append(points)
        descriptors.append(desc)
    if any(desc is None for desc in descriptors):
        raise RuntimeError(f"ORB found no descriptors near frame {index}")
    knn = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(descriptors[0], descriptors[1], k=2)
    ratio_pass = [first for first, second_match in knn if first.distance < 0.75 * second_match.distance]
    ratio_pass.sort(key=lambda match: match.distance)
    inliers = ratio_pass
    if len(ratio_pass) >= 8:
        first_points = np.float32([keypoints[0][m.queryIdx].pt for m in ratio_pass])
        second_points = np.float32([keypoints[1][m.trainIdx].pt for m in ratio_pass])
        _, mask = cv2.findFundamentalMat(first_points, second_points, cv2.FM_RANSAC, 1.5, 0.99)
        if mask is not None:
            inliers = [match for match, keep in zip(ratio_pass, mask.ravel()) if keep]
    shown = inliers[:80]
    canvas = cv2.drawMatches(images[0], keypoints[0], images[1], keypoints[1], shown, None,
                             flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    label = f"Frames {index} / {second} | ORB matches: {len(inliers)} inliers | showing {len(shown)}"
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 40), (20, 25, 35), -1)
    cv2.putText(canvas, label, (12, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)
    cv2.imwrite(str(output), canvas)
    return {"frame_indices": [index, second], "keypoints": [len(k) for k in keypoints],
            "ratio_test_matches": len(ratio_pass), "ransac_inliers": len(inliers), "shown": len(shown)}


def make_video(dataset: Path, frames: list[tuple[float, str]], output: Path) -> float:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to create the RGB preview video")
    # TUM fr1/xyz does not contain an MP4. Use its actual timestamp span to
    # keep the generated RGB preview close to the sequence's real-time pace.
    fps = (len(frames) - 1) / (frames[-1][0] - frames[0][0])
    command = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", f"{fps:.6f}",
               "-pattern_type", "glob", "-i", str(dataset / "rgb" / "*.png"),
               "-c:v", "libx264", "-crf", "25",
               "-pix_fmt", "yuv420p", str(output)]
    subprocess.run(command, check=True)
    return fps


def write_dashboard(output: Path, metrics: dict) -> None:
    ate = metrics.get("ate_rmse_m")
    ate_text = f"{ate:.3f} m" if ate is not None else "No ground truth"
    page = f"""<!doctype html>
<html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ORB-SLAM3 · TUM fr1/xyz</title>
<style>body{{font:16px system-ui;background:#101720;color:#e8eef3;margin:0 auto;max-width:1200px;padding:24px}}
h1{{margin-bottom:4px}}p{{color:#b6c5d1}}.cards{{display:flex;gap:12px;flex-wrap:wrap}}
.card{{background:#202d39;padding:12px 18px;border-radius:10px}}.card strong{{display:block;font-size:22px}}
img,video{{max-width:100%;border-radius:10px;background:white}}section{{margin:25px 0}}
</style><h1>ORB-SLAM3 · 视觉里程计</h1><p>TUM RGB-D freiburg1_xyz · RGB-D 模式 · 真正的 ORB-SLAM3 轨迹</p>
<div class="cards"><div class="card">轨迹位姿<strong>{metrics['trajectory_poses']}</strong></div>
<div class="card">跟踪帧数<strong>{metrics['tracked_frames']}/{metrics['total_frames']}</strong></div>
<div class="card">SE(3) 对齐后 ATE RMSE<strong>{html.escape(ate_text)}</strong></div></div>
<section><h2>输入视频</h2><video controls muted playsinline src="rgb_preview.mp4"></video></section>
<section><h2>相机位置估计</h2><img src="trajectory.png" alt="相机轨迹和真值对比"></section>
<section><h2>ORB 特征匹配：前段</h2><img src="orb_matches_early.png" alt="前段图像对的 ORB 匹配"></section>
<section><h2>ORB 特征匹配：后段</h2><img src="orb_matches_late.png" alt="后段图像对的 ORB 匹配"></section>
<p>匹配图由独立 OpenCV ORB + Hamming 距离 + 比值筛选 + RANSAC 生成，用于可视化；它们不是 ORB-SLAM3 内部逐帧匹配的导出结果。</p>
<p>输入数据和衍生图像：TUM RGB-D Benchmark / J. Sturm 等，<a href="https://cvg.cit.tum.de/data/datasets/rgbd-dataset">CC BY 4.0</a>。</p>
</html>"""
    output.write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="Extracted rgbd_dataset_freiburg1_xyz directory")
    parser.add_argument("--orb-root", type=Path, required=True, help="Built official ORB_SLAM3 checkout")
    parser.add_argument("--binary", type=Path, required=True, help="Built rgbd_tum_headless executable")
    parser.add_argument("--output", type=Path, default=HERE / "results" / "fr1_xyz")
    args = parser.parse_args()
    dataset, root, output = args.dataset.resolve(), args.orb_root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    frames = make_associations(dataset, output / "associations.txt")
    vocabulary = root / "Vocabulary" / "ORBvoc.txt"
    settings = root / "Examples" / "RGB-D" / "TUM1.yaml"
    for required in (vocabulary, settings, args.binary):
        if not required.exists():
            raise FileNotFoundError(required)

    subprocess.run([str(args.binary.resolve()), str(vocabulary), str(settings), str(dataset),
                    str(output / "associations.txt"), str(output)], check=True)
    trajectory = read_tum_trajectory(output / "CameraTrajectory.txt")
    with (output / "position_estimates.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["timestamp", "x_m", "y_m", "z_m", "qx", "qy", "qz", "qw"])
        writer.writerows(trajectory)
    metrics = plot_trajectory(trajectory, dataset / "groundtruth.txt", output / "trajectory.png")
    with (output / "tracking_states.csv").open(newline="", encoding="utf-8") as handle:
        states = list(csv.DictReader(handle))
    metrics.update({"dataset": "TUM freiburg1_xyz", "total_frames": len(states),
                    "tracked_frames": sum(row["state"] == "2" for row in states)})
    metrics["orb_matches_early"] = draw_orb_matches(dataset, frames, max(0, len(frames) // 10),
                                                      output / "orb_matches_early.png")
    metrics["orb_matches_late"] = draw_orb_matches(dataset, frames, max(0, len(frames) * 7 // 10),
                                                     output / "orb_matches_late.png")
    metrics["video_fps"] = make_video(dataset, frames, output / "rgb_preview.mp4")
    (output / "summary.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_dashboard(output / "index.html", metrics)
    print(f"Done: {output / 'index.html'}")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
