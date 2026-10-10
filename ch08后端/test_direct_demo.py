"""Direct solver checks: known motion, degeneracy, identities and real outputs."""

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from direct_alignment import DirectConfig, DirectTracker, align, sample, warp_points
from run_lk_demo import ROOT, run


class DirectTests(unittest.TestCase):
    def setUp(self):
        image = np.random.default_rng(8).integers(0, 256, (240, 320), dtype=np.uint8)
        self.image = cv2.GaussianBlur(image, (5, 5), 0)

    def test_bilinear_sampling(self):
        y, x = np.mgrid[:30, :40]
        xy = np.array([[8.17, 12.83], [22.42, 19.21]])
        np.testing.assert_allclose(sample(2*x+3*y, xy), 2*xy[:, 0]+3*xy[:, 1], atol=1e-12)
        self.assertEqual(warp_points(np.eye(3), []).shape, (0, 2))

    def test_known_projective_motion(self):
        truth = np.array([[1.003, .002, 3.2], [-.001, 1.003, 2.3], [2e-6, -1e-6, 1.]])
        moved = cv2.warpPerspective(self.image, truth, (320, 240))
        estimated, info = align(self.image, moved, DirectConfig(), mask=np.full_like(self.image, 255))
        self.assertTrue(info["valid"])
        probes = np.array([[60, 60], [220, 60], [60, 180], [220, 180]])
        errors = np.linalg.norm(warp_points(estimated, probes)-warp_points(truth, probes), axis=1)
        self.assertLess(float(errors.max()), .2)
        for level in info["levels"]:
            self.assertTrue(all(b <= a+1e-12 for a, b in zip(level["trace"], level["trace"][1:])))

    def test_no_texture_or_single_gradient_rejected(self):
        blank = np.zeros_like(self.image)
        _, info = align(blank, blank, DirectConfig(), mask=np.full_like(blank, 255))
        self.assertFalse(info["valid"])
        stripes = np.tile(((np.arange(320)//8) % 2 * 255).astype(np.uint8), (240, 1))
        _, info = align(stripes, stripes, DirectConfig(), mask=np.full_like(stripes, 255))
        self.assertFalse(info["valid"])

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            align(self.image, self.image[:80], DirectConfig())
        with self.assertRaises(ValueError):
            align(np.zeros((8, 8), np.uint8), np.zeros((8, 8), np.uint8), DirectConfig())

    def test_failed_alignment_does_not_reuse_ids(self):
        tracker = DirectTracker(DirectConfig(max_points=20))
        tracker.update(self.image, 0)
        original = set(tracker.active)
        self.assertTrue(original)
        tracker.update(np.zeros_like(self.image), 1)
        self.assertFalse(tracker.active)
        self.assertFalse(tracker.pairs[-1]["valid"])
        tracker.update(self.image, 2)
        self.assertTrue(tracker.active)
        self.assertTrue(original.isdisjoint(tracker.active))
        self.assertTrue(all(len(tracker.history[i]) == 1 for i in original))

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_report_no_lk_ecc_or_feature_matching(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.avi"
            encoder = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (320, 240))
            self.assertTrue(encoder.isOpened())
            for frame in range(8):
                image = cv2.warpAffine(self.image, np.float32([[1, 0, frame], [0, 1, 0]]), (320, 240))
                encoder.write(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR))
            encoder.release()
            output = root / "results"
            with patch.object(cv2, "calcOpticalFlowPyrLK", side_effect=AssertionError("LK used")), \
                 patch.object(cv2, "findTransformECC", side_effect=AssertionError("ECC used")), \
                 patch.object(cv2, "findHomography", side_effect=AssertionError("Geometric fitting used")):
                summary = run(source, output, DirectConfig(max_points=20), max_frames=6,
                              tracker_class=DirectTracker, label="DIRECT ROAD PLANE", movie_name="direct_tracks.mp4",
                              report_template=ROOT / "direct_report_template.html", error_column="photometric_mae_gray")
            self.assertEqual(summary["frames"], 6)
            self.assertEqual(summary["accepted_pairs"], 5)
            capture = cv2.VideoCapture(str(output / "direct_tracks.mp4"))
            self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 6)
            capture.release()
            with (output / "observations.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertTrue(any(r["is_new"] == "0" for r in rows))
            self.assertTrue(all(0 <= float(r["x_px"]) < 320 and 0 <= float(r["y_px"]) < 240 for r in rows))
            self.assertTrue(all(float(r["fb_error_px"]) <= 1.5 for r in rows))
            self.assertTrue(all(float(r["photometric_mae_gray"]) <= 25 for r in rows))
            self.assertNotIn("__SUMMARY_JSON__", (output / "index.html").read_text())
            for name in ["frame_homographies.csv", "photometric_alignment.jpg", "alignment_diagnostics.json", "trajectories.svg"]:
                self.assertGreater((output / name).stat().st_size, 100)
            pairs = json.loads((output / "alignment_diagnostics.json").read_text())
            self.assertEqual(len(pairs), 5)
            before = (output / "summary.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run(source, output, DirectConfig(), tracker_class=DirectTracker, movie_name="direct_tracks.mp4")
            self.assertEqual(before, (output / "summary.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
