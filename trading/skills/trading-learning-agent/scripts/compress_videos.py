#!/usr/bin/env python3
"""
compress_videos.py — Shrink screen-recording lesson videos to a fraction of their size.

Lecture/chart videos barely move, so low frame rate + higher CRF + mono low-bitrate audio
cuts size ~5-10x while charts and drawings stay readable.

Needs: ffmpeg on PATH.
Usage (Windows PowerShell, from the scripts folder):
    python compress_videos.py --in ..\\..\\..\\..\\profitview-vault\\sources\\youtube\\_video_cache --out ..\\..\\..\\..\\pv-small
    python compress_videos.py --in <dir> --out <dir> --height 480 --fps 4 --crf 36   # even smaller
    python compress_videos.py --in <dir> --out <dir> --split-minutes 10              # 10-minute pieces
"""

import argparse
import subprocess
import sys
from pathlib import Path


def compress(src: Path, dest_dir: Path, height: int, fps: int, crf: int, split_min: int) -> list:
    dest_dir.mkdir(parents=True, exist_ok=True)
    vf = f"scale=-2:'min({height},ih)',fps={fps}"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", vf,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "32k", "-ac", "1", "-ar", "16000", "-movflags", "+faststart"]
    if split_min:
        cmd += ["-f", "segment", "-segment_time", str(split_min * 60), "-reset_timestamps", "1",
                str(dest_dir / f"{src.stem}_part%02d.mp4")]
        outs = lambda: sorted(dest_dir.glob(f"{src.stem}_part*.mp4"))
    else:
        target = dest_dir / f"{src.stem}.mp4"
        cmd.append(str(target))
        outs = lambda: [target] if target.exists() else []
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr else "ffmpeg failed")
    return outs()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--in", dest="src", required=True, help="folder with .mp4 files")
    p.add_argument("--out", required=True, help="output folder")
    p.add_argument("--height", type=int, default=540)
    p.add_argument("--fps", type=int, default=5)
    p.add_argument("--crf", type=int, default=34, help="higher = smaller/blurrier (28-38)")
    p.add_argument("--split-minutes", type=int, default=0)
    a = p.parse_args()
    src_dir, out_dir = Path(a.src), Path(a.out)
    total_in = total_out = 0
    for f in sorted(src_dir.glob("*.mp4")):
        try:
            outs = compress(f, out_dir, a.height, a.fps, a.crf, a.split_minutes)
        except Exception as e:
            print(f"{f.name}: ERROR {e}", file=sys.stderr)
            continue
        a_mb = f.stat().st_size / 1e6
        b_mb = sum(o.stat().st_size for o in outs) / 1e6
        total_in += a_mb
        total_out += b_mb
        print(f"{f.name}: {a_mb:.1f} MB -> {b_mb:.1f} MB in {len(outs)} file(s)")
    print(f"TOTAL: {total_in:.1f} MB -> {total_out:.1f} MB")


if __name__ == "__main__":
    main()
