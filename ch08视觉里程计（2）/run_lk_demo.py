#!/usr/bin/env python3
"""Sparse pyramidal Lucas-Kanade tracks, CSV observations and a local video report."""

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
DEMO_COMMIT = "ce5681be7ef8140560c0e464ef2da611e40b4fc9"
DEMO_URL = f"https://raw.githubusercontent.com/udacity/CarND-LaneLines-P1/{DEMO_COMMIT}/test_videos/solidWhiteRight.mp4"
DEMO_SHA256 = "2d8e14b46fe89afbc8ad1f718685cf09b83e85a324095031c38186a9f0535417"


@dataclass
class Config:
    max_points: int = 180
    min_distance: int = 14
    detect_interval: int = 10
    window: int = 21
    levels: int = 3
    fb_threshold: float = 1.0
    max_lk_error: float = 25.0
    trail_frames: int = 35
    roi_top: float = 0.25


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download_demo(path):
    path = Path(path)
    if path.exists():
        if sha256(path) != DEMO_SHA256:
            raise ValueError(f"Demo checksum mismatch; existing file left untouched: {path}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".download.part")
    with urllib.request.urlopen(DEMO_URL, timeout=60) as response, temporary.open("wb") as stream:
        shutil.copyfileobj(response, stream)
    if sha256(temporary) != DEMO_SHA256:
        raise ValueError(f"Downloaded demo checksum mismatch: {temporary}")
    temporary.replace(path)
    return path


def track_pair(previous, current, points, config):
    """Return predicted coordinates, validity, FB error, and LK patch error."""
    n = len(points)
    empty = (np.zeros((n, 2), np.float32), np.zeros(n, bool),
             np.full(n, np.inf), np.full(n, np.inf))
    if n == 0:
        return empty
    points = np.asarray(points, np.float32).reshape(-1, 1, 2)
    params = dict(winSize=(config.window, config.window), maxLevel=config.levels,
                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, .01))
    predicted, forward_status, patch_error = cv2.calcOpticalFlowPyrLK(previous, current, points, None, **params)
    if predicted is None:
        return empty
    # Replace invalid forward results before calling reverse LK; never feed NaNs to it.
    forward_ok = (forward_status.ravel() == 1) & np.isfinite(predicted.reshape(-1, 2)).all(axis=1)
    safe = predicted.copy()
    safe[~forward_ok] = points[~forward_ok]
    reverse, reverse_status, _ = cv2.calcOpticalFlowPyrLK(current, previous, safe, None, **params)
    if reverse is None:
        return empty
    xy = predicted.reshape(-1, 2)
    fb = np.linalg.norm(reverse.reshape(-1, 2) - points.reshape(-1, 2), axis=1)
    error = patch_error.ravel()
    height, width = current.shape
    valid = (forward_ok & (reverse_status.ravel() == 1) & np.isfinite(fb)
             & np.isfinite(error) & (fb <= config.fb_threshold) & (error <= config.max_lk_error)
             & (xy[:, 0] >= 1) & (xy[:, 0] < width - 1)
             & (xy[:, 1] >= 1) & (xy[:, 1] < height - 1))
    return xy, valid, fb, error


class Tracker:
    def __init__(self, config):
        self.config = config
        self.previous = None
        self.active = {}
        self.history = {}
        self.rejected = 0

    def update(self, gray, frame):
        rows = []
        if self.previous is not None and self.active:
            ids = list(self.active)
            points = np.array([self.active[i] for i in ids], np.float32)
            xy, valid, fb, error = track_pair(self.previous, gray, points, self.config)
            next_active = {}
            for index, track_id in enumerate(ids):
                if not valid[index]:
                    self.rejected += 1
                    continue
                x, y = map(float, xy[index])
                dx, dy = xy[index] - points[index]
                next_active[track_id] = (x, y)
                self.history[track_id].append((frame, x, y))
                rows.append((track_id, x, y, float(dx), float(dy), float(fb[index]), float(error[index]), False))
            self.active = next_active
        # New observations start NEW identities. A lost point is never silently relinked.
        if frame % self.config.detect_interval == 0 or not self.active:
            capacity = self.config.max_points - len(self.active)
            if capacity > 0:
                mask = np.full(gray.shape, 255, np.uint8)
                mask[:int(gray.shape[0] * self.config.roi_top)] = 0
                mask[:3] = mask[-3:] = 0
                mask[:, :3] = mask[:, -3:] = 0
                for xy in self.active.values():
                    cv2.circle(mask, tuple(np.rint(xy).astype(int)), self.config.min_distance, 0, -1)
                corners = cv2.goodFeaturesToTrack(gray, capacity, .015, self.config.min_distance,
                                                 mask=mask, blockSize=7)
                if corners is not None:
                    for xy in corners.reshape(-1, 2):
                        track_id = len(self.history)
                        x, y = map(float, xy)
                        self.history[track_id] = [(frame, x, y)]
                        self.active[track_id] = (x, y)
                        rows.append((track_id, x, y, 0., 0., 0., 0., True))
        self.previous = gray
        return rows


def color(track_id):
    hsv = np.uint8([[[int(track_id * 67 % 180), 210, 255]]])
    return tuple(map(int, cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]))


def render(frame, tracker, number, fps, label="PYRAMIDAL LK"):
    overlay = frame.copy()
    for track_id, xy in tracker.active.items():
        history = tracker.history[track_id]
        if len(history) < 3:
            if getattr(tracker, "show_new_probes", False):
                cv2.circle(overlay, tuple(np.rint(xy).astype(int)), 3, color(track_id), 1, cv2.LINE_AA)
            continue
        recent = [(x, y) for f, x, y in history if f > number - tracker.config.trail_frames]
        if len(recent) > 1:
            cv2.polylines(overlay, [np.rint(recent).astype(np.int32)], False, color(track_id), 2, cv2.LINE_AA)
        cv2.circle(overlay, tuple(np.rint(xy).astype(int)), 3, color(track_id), -1, cv2.LINE_AA)
    height, width = frame.shape[:2]
    canvas = np.zeros((height + 54, 2 * width, 3), np.uint8)
    canvas[:] = (30, 23, 18)
    canvas[54:, :width] = frame
    canvas[54:, width:] = overlay
    cv2.putText(canvas, "ORIGINAL  |  Udacity driving clip", (16, 34), cv2.FONT_HERSHEY_SIMPLEX, .65, (235, 235, 235), 1, cv2.LINE_AA)
    label = f"{label}  |  t={number/fps:.2f}s  |  active={len(tracker.active)}  |  trail={tracker.config.trail_frames}f"
    cv2.putText(canvas, label, (width + 16, 34), cv2.FONT_HERSHEY_SIMPLEX, .65, (235, 235, 235), 1, cv2.LINE_AA)
    return canvas


def run(video, output, config, max_frames=0, max_width=960, overwrite=False, *,
        tracker_class=Tracker, label="PYRAMIDAL LK", movie_name="lk_tracks.mp4",
        report_template=None, error_column="lk_patch_error"):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for browser-compatible H.264 output")
    output = Path(output)
    names = [movie_name, "observations.csv", "summary.json", "index.html", "preview.jpg", "contact_sheet.jpg", "trajectories.svg"]
    if not overwrite and any((output / name).exists() for name in names):
        raise FileExistsError("Outputs already exist. Choose another --output or pass --overwrite.")
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {video}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not math.isfinite(fps) or fps <= 0:
        capture.release()
        raise ValueError("Input video has no valid nominal FPS")
    ok, frame = capture.read()
    if not ok:
        capture.release()
        raise ValueError("Input video contains no decodable frames")
    original_height, original_width = frame.shape[:2]
    width = min(original_width, max_width) // 2 * 2
    height = max(2, round(original_height * width / original_width) // 2 * 2)
    output.mkdir(parents=True, exist_ok=True)
    writer = subprocess.Popen([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
        "-pix_fmt", "bgr24", "-s", f"{2*width}x{height+54}", "-r", str(fps), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output / movie_name)], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    tracker = tracker_class(config)
    snapshots = []
    best_preview, best_score = None, -1.
    active_counts = []
    fb_errors = []
    frame_number = 0
    complete = False
    try:
        with (output / "observations.csv").open("w", newline="", encoding="utf-8") as stream:
            csv_writer = csv.writer(stream)
            csv_writer.writerow(["frame", "time_s", "track_id", "x_px", "y_px", "dx_px", "dy_px", "fb_error_px", error_column, "is_new"])
            while ok and (not max_frames or frame_number < max_frames):
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                rows = tracker.update(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), frame_number)
                for track_id, x, y, dx, dy, fb, error, new in rows:
                    csv_writer.writerow([frame_number, f"{frame_number/fps:.6f}", track_id,
                                         *[f"{v:.5f}" for v in (x, y, dx, dy, fb, error)], int(new)])
                    if not new:
                        fb_errors.append(fb)
                active_counts.append(len(tracker.active))
                canvas = render(frame, tracker, frame_number, fps, label)
                writer.stdin.write(canvas.tobytes())
                if getattr(tracker, "prefer_trajectory_preview", False):
                    score = 0.
                    for track_id in tracker.active:
                        points = tracker.history[track_id]
                        if len(points) >= 3:
                            start = points[max(0, len(points)-config.trail_frames)]
                            end = points[-1]
                            score += math.hypot(end[1]-start[1], end[2]-start[2])
                    if score > best_score:
                        best_score = score
                        best_preview = (frame_number, cv2.resize(canvas, (960, round(canvas.shape[0]*960/canvas.shape[1]))))
                if frame_number % max(1, round(fps * 2)) == 0:
                    snapshots.append((frame_number, cv2.resize(canvas, (960, round(canvas.shape[0] * 960 / canvas.shape[1])))))
                frame_number += 1
                ok, frame = capture.read()
            complete = True
    finally:
        capture.release()
        writer.stdin.close()
        encoding_errors = writer.stderr.read().decode(errors="replace")
        return_code = writer.wait()
        writer.stderr.close()
    if not complete or return_code:
        raise RuntimeError(f"Video encoding failed: {encoding_errors}")
    if frame_number < 2:
        raise ValueError("At least two frames are required for motion tracking")
    # Keep at most four evenly spaced comparison snapshots.
    selected = [snapshots[i] for i in np.linspace(0, len(snapshots) - 1, min(4, len(snapshots)), dtype=int)]
    if best_preview is not None:
        # Preserve temporal ordering and include a frame with real long trails.
        selected = sorted([*selected[:2], best_preview, selected[-1]], key=lambda item: item[0])
    cv2.imwrite(str(output / "preview.jpg"), (best_preview or selected[-1])[1])
    cv2.imwrite(str(output / "contact_sheet.jpg"), np.vstack([image for _, image in selected]))
    candidates = sorted(tracker.history, key=lambda i: (len(tracker.history[i]), -i), reverse=True)
    # Deterministic long-lived tracks with spatially separated starting pixels.
    example_ids = []
    for track_id in candidates:
        if len(tracker.history[track_id]) < 3:
            continue
        start = np.array(tracker.history[track_id][0][1:])
        if all(np.linalg.norm(start - np.array(tracker.history[i][0][1:])) > 70 for i in example_ids):
            example_ids.append(track_id)
        if len(example_ids) == 6:
            break
    examples = [{"id": i, "color": "#%02x%02x%02x" % color(i)[::-1],
                 "points": [[f, round(x, 3), round(y, 3)] for f, x, y in tracker.history[i]]} for i in example_ids]
    lifetimes = [len(points) for points in tracker.history.values()]
    input_digest = sha256(video)
    summary = {"input_name": Path(video).name, "input_sha256": input_digest, "demo_source_url": DEMO_URL if input_digest == DEMO_SHA256 else None,
               "frames": frame_number, "fps": fps, "duration_s": frame_number / fps,
               "tracking_size": [width, height], "input_size": [original_width, original_height],
               "total_track_ids": len(tracker.history), "lost_track_ids": tracker.rejected,
               "mean_active_points": float(np.mean(active_counts)), "max_lifetime_frames": max(lifetimes, default=0),
               "median_fb_error_px": float(np.median(fb_errors)) if fb_errors else None,
               "parameters": asdict(config), "examples": examples,
               "note": "Image-plane pixel tracks, not 3D camera/vehicle motion. Time uses nominal CFR frame/fps."}
    if best_preview is not None:
        summary["preview_frame"] = best_preview[0]
    if hasattr(tracker, "write_diagnostics"):
        summary.update(tracker.write_diagnostics(output))
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    template = (report_template or ROOT / "report_template.html").read_text(encoding="utf-8")
    (output / "index.html").write_text(template.replace("__SUMMARY_JSON__", json.dumps(summary, ensure_ascii=False).replace("<", "\\u003c")), encoding="utf-8")
    (output / "trajectories.svg").write_text(trajectory_svg(examples, width, height, label), encoding="utf-8")
    return summary


def trajectory_svg(examples, width, height, label="LK"):
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="640" viewBox="0 0 1000 640" role="img" aria-label="Selected pixel trajectories in image coordinates">',
                '<rect width="1000" height="640" fill="#0c1524"/>',
                f'<text x="70" y="32" fill="#e3edf8" font-family="sans-serif" font-size="20">{label} pixel tracks | x right, y down | circles = start</text>',
                '<rect x="70" y="65" width="860" height="500" fill="none" stroke="#42556c"/>']
    for tick in range(6):
        x = 70 + tick / 5 * 860
        y = 65 + tick / 5 * 500
        elements += [f'<text x="{x}" y="589" fill="#b6c7db" font-size="14" text-anchor="middle">{tick/5*width:.0f}</text>',
                     f'<text x="57" y="{y+5}" fill="#b6c7db" font-size="14" text-anchor="end">{tick/5*height:.0f}</text>']
    for example in examples:
        points = [(70+x/width*860, 65+y/height*500) for _, x, y in example["points"]]
        coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        x, y = points[0]
        elements += [f'<polyline points="{coords}" fill="none" stroke="{example["color"]}" stroke-width="2.5"/>',
                     f'<circle cx="{x}" cy="{y}" r="5" fill="none" stroke="{example["color"]}" stroke-width="2"/>',
                     f'<text x="{x+9}" y="{y-9}" fill="{example["color"]}" font-size="15">ID {example["id"]}</text>']
    elements += ['<text x="500" y="626" fill="#e3edf8" font-size="16" text-anchor="middle">x (px)</text>',
                 '<text x="22" y="320" fill="#e3edf8" font-size="16" transform="rotate(-90 22 320)">y (px)</text>', '</svg>']
    return "\n".join(elements)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, help="Your local driving video")
    parser.add_argument("--download-demo", action="store_true", help="Download the pinned Udacity example")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "driving_lk")
    parser.add_argument("--max-frames", type=int, default=0, help="0 = entire video")
    parser.add_argument("--max-width", type=int, default=960)
    parser.add_argument("--max-points", type=int, default=180)
    parser.add_argument("--fb-threshold", type=float, default=1.0)
    parser.add_argument("--trail-frames", type=int, default=35)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.video and args.download_demo:
        parser.error("Choose either --video or --download-demo")
    if not args.video and not args.download_demo:
        parser.error("Provide --video or --download-demo")
    if args.max_frames < 0 or args.max_width < 160 or args.max_points < 1 or not math.isfinite(args.fb_threshold) or args.fb_threshold <= 0 or args.trail_frames < 2:
        parser.error("Invalid numeric argument")
    video = args.video or download_demo(ROOT / ".cache" / "solidWhiteRight.mp4")
    config = Config(max_points=args.max_points, fb_threshold=args.fb_threshold, trail_frames=args.trail_frames)
    summary = run(video, args.output, config, args.max_frames, args.max_width, args.overwrite)
    print(json.dumps({k: v for k, v in summary.items() if k != "examples"}, ensure_ascii=False, indent=2))
    print(f"Report: {args.output.resolve() / 'index.html'}")


if __name__ == "__main__":
    main()
