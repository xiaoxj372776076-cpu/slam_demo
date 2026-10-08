"""Small, dataset-free checks for the demo's data and alignment logic."""

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from run_demo import draw_orb_matches, make_associations, read_tum_trajectory, rigid_align


class DemoTests(unittest.TestCase):
    def test_timestamp_associations_choose_nearest_depth(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rgb.txt").write_text(
                "# RGB timestamps\n" + "".join(f"{i:.3f} rgb/{i}.png\n" for i in range(21)))
            (root / "depth.txt").write_text(
                "".join(f"{i + 0.005:.3f} depth/{i}.png\n" for i in range(21)))
            pairs = make_associations(root, root / "associations.txt")
            self.assertEqual(len(pairs), 21)
            self.assertIn("depth/20.png", (root / "associations.txt").read_text())

    def test_rigid_alignment_keeps_metric_scale(self):
        source = np.array([[0., 0., 0.], [1., 0., 0.], [0., 2., 0.], [0., 0., 3.]])
        rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        target = source @ rotation + np.array([3., -2., 1.])
        aligned, _, _ = rigid_align(source, target)
        np.testing.assert_allclose(aligned, target, atol=1e-12)

    def test_tum_trajectory_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CameraTrajectory.txt"
            path.write_text("# comment\n1.0 0.1 0.2 0.3 0 0 0 1\n")
            trajectory = read_tum_trajectory(path)
            self.assertEqual(trajectory.shape, (1, 8))
            self.assertAlmostEqual(trajectory[0, 3], 0.3)

    def test_orb_match_visualization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rgb").mkdir()
            image = np.random.default_rng(7).integers(0, 256, (240, 320, 3), dtype=np.uint8)
            cv2.imwrite(str(root / "rgb" / "0.png"), image)
            cv2.imwrite(str(root / "rgb" / "8.png"), np.roll(image, 5, axis=1))
            frames = [(float(i), f"rgb/{i}.png") for i in range(9)]
            summary = draw_orb_matches(root, frames, 0, root / "matches.png")
            self.assertGreater(summary["ransac_inliers"], 10)
            self.assertTrue((root / "matches.png").is_file())


if __name__ == "__main__":
    unittest.main()
