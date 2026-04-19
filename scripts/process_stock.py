"""Pre-process raw stock video files into 300-second clips for the pipeline.

Usage:
    python scripts/process_stock.py /path/to/raw/footage/

Places output clips in the `stock/` directory relative to where you run
the script (i.e. the project root).

Requirements: MoviePy (pip install moviepy) and a working ffmpeg install.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from moviepy.editor import VideoFileClip


def process(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stocks = [f for f in input_dir.iterdir() if "stock" in f.name and f.suffix == ".mp4"]
    print(f"Found {len(stocks)} stock file(s) in {input_dir}")

    for stock_path in stocks:
        try:
            video = VideoFileClip(str(stock_path))
            video = video.subclip(30, video.duration)
            video = video.resize(height=1280)
            if video.w > 720:
                video = video.crop(x_center=video.w / 2, width=720)

            clips_num = int(video.duration / 150)
            if clips_num == 0:
                print(f"  {stock_path.name}: too short, skipping")
                continue

            start_inc = (video.duration - 300) / clips_num
            for i in range(clips_num):
                try:
                    clip = video.subclip(i * start_inc, i * start_inc + 300)
                    ts = datetime.now().strftime("%H%M%S%f")
                    out = output_dir / f"clip{ts}.mp4"
                    clip.write_videofile(str(out), fps=60, threads=os.cpu_count() or 4)
                except Exception as e:
                    print(f"  Clip {i} error: {e}")
        except Exception as e:
            print(f"  {stock_path.name} error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-process stock footage.")
    parser.add_argument("input_dir", nargs="?", default=".", help="Directory containing raw stock MP4s.")
    parser.add_argument("--out", default="stock", help="Output directory for processed clips.")
    args = parser.parse_args()
    process(Path(args.input_dir), Path(args.out))
