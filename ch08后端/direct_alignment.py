"""Road-plane direct photometric alignment: custom 8-DoF homography GN solver.

No feature matching, OpenCV LK, ECC, or geometric RANSAC is used here.
All reference pixels share ONE homography. This is 2D alignment, not SE(3) VO.
"""

import csv
import json
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class DirectConfig:
    max_points: int = 100
    min_distance: int = 16
    corner_quality: float = .003
    detect_interval: int = 10
    trail_frames: int = 35
    levels: int = 3
    iterations: int = 20
    sample_step: int = 3
    max_samples: int = 3500
    gradient_threshold: float = .004
    huber_delta: float = .03
    fb_threshold: float = 1.5
    max_photo_error: float = 25.
    max_pair_motion: float = 90.
    min_inlier_ratio: float = .65


def road_mask(shape):
    """Explicit demo ROI: approximate road trapezoid, not a semantic detector."""
    height, width = shape
    vertices = np.float32([[.38, .61], [.65, .61], [.98, .97], [.02, .97]])
    vertices *= (width, height)
    mask = np.zeros(shape, np.uint8)
    cv2.fillConvexPoly(mask, np.rint(vertices).astype(np.int32), 255)
    return mask


def warp_points(homography, points):
    points = np.asarray(points, np.float64).reshape(-1, 2)
    homogeneous = np.column_stack([points, np.ones(len(points))]) @ homography.T
    with np.errstate(divide="ignore", invalid="ignore"):
        return homogeneous[:, :2] / homogeneous[:, 2:]


def sample(image, xy):
    """True bilinear interpolation, not remap's quantized interpolation table."""
    x, y = np.asarray(xy).T
    x = np.clip(x, 0, image.shape[1] - 1.001)
    y = np.clip(y, 0, image.shape[0] - 1.001)
    ix, iy = x.astype(int), y.astype(int)
    ax, ay = x - ix, y - iy
    return ((1-ax)*(1-ay)*image[iy, ix] + ax*(1-ay)*image[iy, ix+1]
            + (1-ax)*ay*image[iy+1, ix] + ax*ay*image[iy+1, ix+1])


def normalization(shape):
    height, width = shape
    scale = max(height, width)
    return np.array([[1/scale, 0, -(width-1)/2/scale],
                     [0, 1/scale, -(height-1)/2/scale], [0, 0, 1.]]), scale


def huber(residual, delta):
    absolute = np.abs(residual)
    return np.where(absolute <= delta, .5*residual**2, delta*(absolute-.5*delta))


def road_initialization(reference, current, mask, previous, config):
    """Small photometric hypothesis search, not feature/geometric matching.

    Road edges suffer an aperture ambiguity. Test inward/outward projective
    expansions around an approximate image vanishing point to avoid the
    identity local minimum. This is ONLY initialization; GN optimizes all 8 DoF.
    The center is an image-coordinate heuristic, not a calibrated camera value.
    """
    height, width = reference.shape
    gx = cv2.Sobel(reference.astype(float)/255, cv2.CV_64F, 1, 0, scale=1/8)
    gy = cv2.Sobel(reference.astype(float)/255, cv2.CV_64F, 0, 1, scale=1/8)
    yy, xx = np.mgrid[40:height-40:config.sample_step, 40:width-40:config.sample_step]
    points = np.column_stack([xx.ravel(), yy.ravel()])
    keep = (mask[yy, xx].ravel() > 0) & (np.hypot(gx[yy, xx], gy[yy, xx]).ravel() > config.gradient_threshold)
    points = points[keep]
    if not len(points):
        return previous
    points = points[np.linspace(0, len(points)-1, min(len(points), config.max_samples), dtype=int)]
    target = sample(reference, points)/255
    candidates = [previous, np.eye(3)]
    u, v = width*.5, height*.55
    for alpha in [-.5, -.25, .25, .5, .75]:
        beta = alpha/width
        candidates.append(np.array([[1, -u*beta, u*v*beta], [0, 1-v*beta, v*v*beta], [0, -beta, 1+v*beta]]))
    costs = []
    for h in candidates:
        xy = warp_points(h, points)
        visible = (np.isfinite(xy).all(axis=1) & (xy[:, 0] >= 1) & (xy[:, 0] < width-2)
                   & (xy[:, 1] >= 1) & (xy[:, 1] < height-2))
        losses = np.full(len(points), float(huber(1., config.huber_delta)))
        losses[visible] = huber(sample(current, xy[visible])/255-target[visible], config.huber_delta)
        costs.append(float(losses.mean()))
    return candidates[int(np.argmin(costs))]


def optimize_level(reference, current, mask, initial, config, level):
    ref = reference.astype(np.float64) / 255
    image = current.astype(np.float64) / 255
    gx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3, scale=1/8)
    gy = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3, scale=1/8)
    rgx = cv2.Sobel(ref, cv2.CV_64F, 1, 0, ksize=3, scale=1/8)
    rgy = cv2.Sobel(ref, cv2.CV_64F, 0, 1, ksize=3, scale=1/8)
    yy, xx = np.mgrid[2:ref.shape[0]-2:config.sample_step, 2:ref.shape[1]-2:config.sample_step]
    xy = np.column_stack([xx.ravel(), yy.ravel()])
    strength = np.hypot(rgx[yy, xx], rgy[yy, xx]).ravel()
    keep = (mask[yy, xx].ravel() > 0) & (strength > config.gradient_threshold)
    # Reserve a boundary margin for outward road motion. Otherwise one sample
    # near the image edge can forbid every physically correct GN step.
    margin = max(2, 40 / (2**level))
    keep &= ((xy[:, 0] >= margin) & (xy[:, 0] < ref.shape[1]-margin)
             & (xy[:, 1] >= margin) & (xy[:, 1] < ref.shape[0]-margin))
    xy, strength = xy[keep], strength[keep]
    if len(xy) > config.max_samples:
        # Even deterministic subsampling avoids selecting only one dominant edge.
        xy = xy[np.linspace(0, len(xy)-1, config.max_samples, dtype=int)]
    if len(xy) < 32:
        return initial, {"level": level, "usable": False, "samples": len(xy), "trace": []}
    n, scale = normalization(ref.shape)
    n_inv = np.linalg.inv(n)
    q = warp_points(n, xy)
    target = sample(ref, xy)
    h = n @ initial @ n_inv
    h /= h[2, 2]
    damping = 1e-3
    trace = []
    solvable = False
    for iteration in range(config.iterations):
        transformed = warp_points(h, q)
        pixel = warp_points(n_inv, transformed)
        visible = (np.isfinite(pixel).all(axis=1) & (pixel[:, 0] >= 1) & (pixel[:, 0] < ref.shape[1]-2)
                   & (pixel[:, 1] >= 1) & (pixel[:, 1] < ref.shape[0]-2))
        if visible.sum() < 32 or visible.mean() < .65:
            break
        points = q[visible]
        projected = transformed[visible]
        pixels = pixel[visible]
        residual = sample(image, pixels) - target[visible]
        cost = float(np.mean(huber(residual, config.huber_delta)))
        if not trace:
            trace.append(cost)
        x, y = points.T
        u, v = projected.T
        denominator = h[2, 0]*x + h[2, 1]*y + 1
        a, b, c = x/denominator, y/denominator, 1/denominator
        zeros = np.zeros(len(x))
        du = np.column_stack([a, b, c, zeros, zeros, zeros, -u*a, -u*b])
        dv = np.column_stack([zeros, zeros, zeros, a, b, c, -v*a, -v*b])
        jacobian = scale * (sample(gx, pixels)[:, None]*du + sample(gy, pixels)[:, None]*dv)
        weights = np.minimum(1., config.huber_delta / np.maximum(np.abs(residual), 1e-12))
        normal = jacobian.T @ (weights[:, None]*jacobian)
        gradient = jacobian.T @ (weights*residual)
        if np.linalg.matrix_rank(normal, tol=1e-8) < 8:
            break
        solvable = True
        accepted = False
        for _ in range(8):
            try:
                delta = -np.linalg.solve(normal + damping*np.diag(np.maximum(np.diag(normal), 1e-6)), gradient)
            except np.linalg.LinAlgError:
                break
            trial = h.copy()
            trial.flat[:8] += delta
            trial_pixel = warp_points(n_inv, warp_points(trial, points))
            in_bounds = (np.isfinite(trial_pixel).all(axis=1) & (trial_pixel[:, 0] >= 1)
                         & (trial_pixel[:, 0] < ref.shape[1]-2) & (trial_pixel[:, 1] >= 1)
                         & (trial_pixel[:, 1] < ref.shape[0]-2))
            # A trial cannot lower cost simply by dropping inconvenient samples.
            if in_bounds.all():
                trial_residual = sample(image, trial_pixel) - target[visible]
                trial_cost = float(np.mean(huber(trial_residual, config.huber_delta)))
                if trial_cost <= cost:
                    h = trial
                    trace.append(trial_cost)
                    damping = max(1e-6, damping*.3)
                    accepted = True
                    break
            damping *= 10
        if not accepted or np.linalg.norm(delta) < 1e-5:
            break
    result = n_inv @ h @ n
    result /= result[2, 2]
    return result, {"level": level, "usable": solvable, "samples": len(xy), "trace": trace}


def align(reference, current, config, initial=None, mask=None):
    if reference.shape != current.shape or reference.ndim != 2:
        raise ValueError("Direct alignment needs equal-sized grayscale images")
    if min(reference.shape) < 16:
        raise ValueError("Images are too small")
    mask = road_mask(reference.shape) if mask is None else mask
    refs, images, masks = [reference], [current], [mask]
    for _ in range(config.levels):
        if min(refs[-1].shape) < 40:
            break
        refs.append(cv2.pyrDown(refs[-1]))
        images.append(cv2.pyrDown(images[-1]))
        masks.append(cv2.resize(mask, (refs[-1].shape[1], refs[-1].shape[0]), interpolation=cv2.INTER_NEAREST))
    h = np.eye(3) if initial is None else np.array(initial, np.float64)
    diagnostics = []
    for level in range(len(refs)-1, -1, -1):
        scale = np.diag([1/(2**level), 1/(2**level), 1.])
        scaled, diagnostic = optimize_level(refs[level], images[level], masks[level], scale@h@np.linalg.inv(scale), config, level)
        h = np.linalg.inv(scale)@scaled@scale
        h /= h[2, 2]
        diagnostics.append(diagnostic)
    # Quality is measured on a fixed ROI grid, independently of optimizer samples.
    yy, xx = np.mgrid[3:reference.shape[0]-3:4, 3:reference.shape[1]-3:4]
    xy = np.column_stack([xx.ravel(), yy.ravel()])
    xy = xy[mask[yy, xx].ravel() > 0]
    mapped = warp_points(h, xy)
    height, width = reference.shape
    visible = (np.isfinite(mapped).all(axis=1) & (mapped[:, 0] >= 1) & (mapped[:, 0] < width-2)
               & (mapped[:, 1] >= 1) & (mapped[:, 1] < height-2))
    errors = np.abs(sample(current, mapped[visible]) - sample(reference, xy[visible])) if visible.any() else np.array([255.])
    motion = np.linalg.norm(mapped[visible]-xy[visible], axis=1) if visible.any() else np.array([np.inf])
    ratio = float(np.mean(errors < config.max_photo_error))
    valid = (any(d["usable"] for d in diagnostics) and len(xy) > 0 and visible.mean() > .65
             and ratio >= config.min_inlier_ratio and np.percentile(motion, 95) < config.max_pair_motion
             and np.isfinite(h).all() and abs(np.linalg.det(h)) > 1e-8)
    return h, {"valid": bool(valid), "mae_gray": float(np.mean(errors)), "inlier_ratio": ratio,
               "coverage": float(visible.mean()) if len(xy) else 0., "levels": diagnostics}


class DirectTracker:
    show_new_probes = True
    prefer_trajectory_preview = True

    def __init__(self, config):
        self.config = config
        self.previous = None
        self.last_h = np.eye(3)
        self.active = {}
        self.history = {}
        self.rejected = 0
        self.pairs = []
        self.diagnostic_image = None
        self.diagnostic_summary = {}

    def update(self, gray, frame):
        rows = []
        mask = road_mask(gray.shape)
        if self.previous is not None:
            initial = road_initialization(self.previous, gray, mask, self.last_h, self.config)
            h, info = align(self.previous, gray, self.config, initial, mask)
            # Compare the same physical road region in both directions, rather
            # than two unrelated fixed image-coordinate trapezoids.
            reverse, reverse_info = np.eye(3), {"valid": False}
            if info["valid"]:
                reverse_mask = cv2.warpPerspective(mask, h, (gray.shape[1], gray.shape[0]), flags=cv2.INTER_NEAREST)
                reverse, reverse_info = align(gray, self.previous, self.config, np.linalg.inv(h), reverse_mask)
            valid_pair = info["valid"] and reverse_info["valid"]
            info.update(frame=frame, valid=valid_pair, homography=h.tolist())
            info["reverse"] = reverse_info
            self.pairs.append(info)
            self.last_h = h if valid_pair else np.eye(3)
            ids = list(self.active)
            points = np.array([self.active[i] for i in ids], np.float64).reshape(-1, 2)
            mapped = warp_points(h, points)
            back = warp_points(reverse, mapped)
            fb = np.linalg.norm(back-points, axis=1)
            next_active = {}
            offsets = np.array([(x, y) for y in range(-3, 4) for x in range(-3, 4)])
            for index, track_id in enumerate(ids):
                xy = mapped[index]
                inside = (np.isfinite(xy).all() and 5 <= xy[0] < gray.shape[1]-5 and 5 <= xy[1] < gray.shape[0]-5)
                photo = np.inf
                if inside:
                    source_patch = points[index] + offsets
                    current_patch = warp_points(h, source_patch)
                    patch_inside = (np.isfinite(current_patch).all() and (current_patch[:, 0] >= 0).all()
                                    and (current_patch[:, 0] < gray.shape[1]-1).all()
                                    and (current_patch[:, 1] >= 0).all()
                                    and (current_patch[:, 1] < gray.shape[0]-1).all())
                    if patch_inside:
                        photo = float(np.mean(np.abs(sample(gray, current_patch)-sample(self.previous, source_patch))))
                if not (valid_pair and inside and fb[index] <= self.config.fb_threshold and photo <= self.config.max_photo_error):
                    self.rejected += 1
                    continue
                x, y = map(float, xy)
                dx, dy = xy-points[index]
                next_active[track_id] = (x, y)
                self.history[track_id].append((frame, x, y))
                rows.append((track_id, x, y, float(dx), float(dy), float(fb[index]), photo, False))
            self.active = next_active
            if frame == 100 or self.diagnostic_image is None:
                aligned = cv2.warpPerspective(gray, h, (gray.shape[1], gray.shape[0]), flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP)
                tiles = []
                for image, title in [(self.previous, "REFERENCE"), (gray, "CURRENT (unaligned)"), (aligned, "CURRENT warped to reference"),
                                     (cv2.absdiff(self.previous, gray), "ABS ERROR before"), (cv2.absdiff(self.previous, aligned), "ABS ERROR after")]:
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                    cv2.polylines(image, [np.int32([[.38*gray.shape[1], .61*gray.shape[0]], [.65*gray.shape[1], .61*gray.shape[0]], [.98*gray.shape[1], .97*gray.shape[0]], [.02*gray.shape[1], .97*gray.shape[0]]])], True, (0, 200, 255), 2)
                    tile = cv2.resize(image, (480, 270))
                    cv2.putText(tile, title, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 210, 80), 1, cv2.LINE_AA)
                    tiles.append(tile)
                grid_y, grid_x = np.mgrid[:gray.shape[0], :gray.shape[1]]
                warped_grid = warp_points(h, np.column_stack([grid_x.ravel(), grid_y.ravel()])).reshape(*gray.shape, 2)
                valid_roi = ((mask > 0) & (warped_grid[:, :, 0] >= 0) & (warped_grid[:, :, 0] < gray.shape[1]-1)
                             & (warped_grid[:, :, 1] >= 0) & (warped_grid[:, :, 1] < gray.shape[0]-1))
                before = float(cv2.absdiff(self.previous, gray)[valid_roi].mean()) if valid_roi.any() else None
                after = float(cv2.absdiff(self.previous, aligned)[valid_roi].mean()) if valid_roi.any() else None
                self.diagnostic_summary = {"frame": frame, "mae_before": before, "mae_after": after, "accepted": valid_pair}
                legend = np.zeros_like(tiles[0])
                for line, text in enumerate([f"PAIR {frame-1} -> {frame}", "Valid overlapping road ROI only",
                                            f"MAE before: {before:.2f}" if before is not None else "No ROI overlap",
                                            f"MAE after:  {after:.2f}" if after is not None else "No ROI overlap",
                                            "Gray range: 0 .. 255", "2D planar model, NOT camera pose"]):
                    cv2.putText(legend, text, (16, 40+line*32), cv2.FONT_HERSHEY_SIMPLEX, .55, (230, 230, 230), 1, cv2.LINE_AA)
                self.diagnostic_image = np.vstack([np.hstack(tiles[:3]), np.hstack([tiles[3], tiles[4], legend])])
        if frame % self.config.detect_interval == 0 or not self.active:
            for xy in self.active.values():
                cv2.circle(mask, tuple(np.rint(xy).astype(int)), self.config.min_distance, 0, -1)
            count = self.config.max_points-len(self.active)
            corners = cv2.goodFeaturesToTrack(gray, count, self.config.corner_quality, self.config.min_distance, mask=mask, blockSize=7) if count > 0 else None
            if corners is not None:
                for x, y in corners.reshape(-1, 2):
                    track_id = len(self.history)
                    self.active[track_id] = (float(x), float(y))
                    self.history[track_id] = [(frame, float(x), float(y))]
                    rows.append((track_id, float(x), float(y), 0., 0., 0., 0., True))
        self.previous = gray
        if frame % 25 == 0:
            print(f"Direct alignment: frame {frame}, active probes {len(self.active)}", flush=True)
        return rows

    def write_diagnostics(self, output):
        (output / "alignment_diagnostics.json").write_text(json.dumps(self.pairs, indent=2), encoding="utf-8")
        with (output / "frame_homographies.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["frame", "accepted", "mae_gray", "inlier_ratio", *[f"h{i}{j}" for i in range(3) for j in range(3)]])
            for pair in self.pairs:
                writer.writerow([pair["frame"], int(pair["valid"]), pair["mae_gray"], pair["inlier_ratio"], *np.array(pair["homography"]).ravel()])
        if self.diagnostic_image is not None:
            cv2.imwrite(str(output / "photometric_alignment.jpg"), self.diagnostic_image)
        return {"method": "Direct photometric road-plane homography (8 DoF), not SE(3) VO",
                "accepted_pairs": sum(pair["valid"] for pair in self.pairs), "total_pairs": len(self.pairs),
                "diagnostic": self.diagnostic_summary,
                "note": "Model-projected 2D road-plane probes; not independent per-pixel motion or 3D vehicle pose."}
