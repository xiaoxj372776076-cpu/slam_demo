"""Dataset-free LK accuracy checks and a real encoder/report smoke test."""

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from run_lk_demo import Config, Tracker, run, track_pair
from serve_results import byte_range


class LKTests(unittest.TestCase):
    def test_http_byte_ranges(self):
        self.assertEqual(byte_range("bytes=10-19", 100), (10, 19))
        self.assertEqual(byte_range("bytes=90-", 100), (90, 99))
        self.assertEqual(byte_range("bytes=-5", 100), (95, 99))
        for header in ("bytes=101-", "bytes=5-2", "bytes=-0", "bytes=0-1,3-4"):
            with self.assertRaises(ValueError):
                byte_range(header, 100)

    def setUp(self):
        self.image = np.random.default_rng(8).integers(0, 256, (180, 240), dtype=np.uint8)
        self.image = cv2.GaussianBlur(self.image, (5, 5), 0)

    def test_known_translation(self):
        # Keep the pyramid windows away from the synthetic warp's black border.
        image = np.random.default_rng(8).integers(0, 256, (540, 960), dtype=np.uint8)
        image = cv2.GaussianBlur(image, (5, 5), 0)
        moved = cv2.warpAffine(image, np.float32([[1, 0, 3], [0, 1, 2]]), (960, 540))
        points = np.array([[240, 180], [480, 180], [240, 360], [480, 360]], np.float32)
        result, valid, fb, _ = track_pair(image, moved, points, Config())
        self.assertTrue(valid.all())
        np.testing.assert_allclose(result - points, np.tile([3, 2], (4, 1)), atol=.12)
        self.assertLess(float(fb.max()), .1)

    def test_empty_points_and_textureless_input(self):
        image = np.zeros_like(self.image)
        result, valid, _, _ = track_pair(image, image, [], Config())
        self.assertEqual(result.shape, (0, 2))
        self.assertEqual(valid.size, 0)
        tracker = Tracker(Config())
        self.assertEqual(tracker.update(image, 0), [])
        self.assertEqual(tracker.update(image, 1), [])

    def test_tracks_do_not_reuse_lost_ids(self):
        tracker = Tracker(Config(max_points=20))
        tracker.update(self.image, 0)
        initial = set(tracker.active)
        self.assertTrue(initial)
        tracker.update(np.zeros_like(self.image), 1)
        lost = initial - set(tracker.active)
        self.assertTrue(lost)
        lengths = {i: len(tracker.history[i]) for i in lost}
        tracker.update(self.image, 2)
        self.assertTrue(all(i not in tracker.active for i in lost))
        self.assertEqual(lengths, {i: len(tracker.history[i]) for i in lost})
        self.assertLessEqual(len(tracker.active), 20)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_end_to_end_report_and_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.avi"
            encoder = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (240, 180))
            self.assertTrue(encoder.isOpened())
            for frame in range(8):
                image = cv2.warpAffine(self.image, np.float32([[1, 0, frame], [0, 1, 0]]), (240, 180))
                encoder.write(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR))
            encoder.release()
            output = root / "results"
            summary = run(source, output, Config(max_points=20), max_frames=6)
            self.assertEqual(summary["frames"], 6)
            self.assertEqual(summary["tracking_size"], [240, 180])
            capture = cv2.VideoCapture(str(output / "lk_tracks.mp4"))
            self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 6)
            capture.release()
            with (output / "observations.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertTrue(rows)
            self.assertTrue(all(0 <= float(r["x_px"]) < 240 and 0 <= float(r["y_px"]) < 180 for r in rows))
            self.assertTrue(all(float(r["fb_error_px"]) <= 1 for r in rows))
            self.assertEqual(json.loads((output / "summary.json").read_text())["frames"], 6)
            self.assertNotIn("__SUMMARY_JSON__", (output / "index.html").read_text())
            for name in ["preview.jpg", "contact_sheet.jpg", "trajectories.svg"]:
                self.assertGreater((output / name).stat().st_size, 100)
            before = (output / "summary.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run(source, output, Config())
            self.assertEqual(before, (output / "summary.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
