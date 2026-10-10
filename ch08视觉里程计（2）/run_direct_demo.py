#!/usr/bin/env python3
"""Direct road-plane photometric alignment on the same driving clip as the LK demo."""

import argparse
import json
from pathlib import Path

from direct_alignment import DirectConfig, DirectTracker
from run_lk_demo import ROOT, download_demo, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--download-demo", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "results/driving_direct")
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--max-width", type=int, default=960)
    parser.add_argument("--max-points", type=int, default=100)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if bool(args.video) == bool(args.download_demo):
        parser.error("Choose either --video or --download-demo")
    if args.max_frames < 0 or args.max_width < 160 or args.max_points < 1:
        parser.error("Invalid numeric argument")
    video = args.video or download_demo(ROOT / ".cache/solidWhiteRight.mp4")
    summary = run(video, args.output, DirectConfig(max_points=args.max_points), args.max_frames, args.max_width,
                  args.overwrite, tracker_class=DirectTracker, label="DIRECT ROAD PLANE",
                  movie_name="direct_tracks.mp4", report_template=ROOT / "direct_report_template.html",
                  error_column="photometric_mae_gray")
    print(json.dumps({k: v for k, v in summary.items() if k != "examples"}, indent=2, ensure_ascii=False))
    print(f"Report: {args.output.resolve() / 'index.html'}")


if __name__ == "__main__":
    main()
