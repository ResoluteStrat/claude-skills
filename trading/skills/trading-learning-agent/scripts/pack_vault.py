#!/usr/bin/env python3
"""
pack_vault.py — Shrink a vault's media into a small upload bundle.

Skips downloaded videos, resizes frames (max width 1280, JPEG quality 70) and drops
near-duplicate consecutive frames (typical for lecture videos where the chart barely changes).

Needs: pip install pillow
Usage:
    python pack_vault.py --vault-dir ..\\..\\..\\..\\profitview-vault --out ..\\..\\..\\..\\pv-pack [--diff 6]
Output: <out>/media/<id>/frame_*.jpg + frames.md, <out>/whisper/*.txt, and a size report.
"""

import argparse
import shutil
from pathlib import Path

from PIL import Image


def _thumb(img):
    return list(img.convert("L").resize((32, 18)).getdata())


def _diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def pack(vault: Path, out: Path, threshold: float, max_w: int = 1280):
    src = vault / "sources" / "youtube"
    out.mkdir(parents=True, exist_ok=True)
    kept_total = dropped_total = 0
    for vid_dir in sorted((src / "media").glob("*")):
        if not vid_dir.is_dir():
            continue
        dest = out / "media" / vid_dir.name
        dest.mkdir(parents=True, exist_ok=True)
        prev, rows = None, []
        for f in sorted(vid_dir.glob("frame_*.jpg")):
            img = Image.open(f)
            t = _thumb(img)
            if prev is not None and _diff(prev, t) < threshold:
                dropped_total += 1
                continue
            prev = t
            if img.width > max_w:
                img = img.resize((max_w, round(img.height * max_w / img.width)))
            img.convert("RGB").save(dest / f.name, "JPEG", quality=70, optimize=True)
            rows.append(f.name)
            kept_total += 1
        (dest / "frames.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    wh = src / "whisper"
    if wh.exists():
        shutil.copytree(wh, out / "whisper", dirs_exist_ok=True)
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) / 1e6
    print(f"kept {kept_total} frames, dropped {dropped_total} near-duplicates, bundle = {size:.1f} MB")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vault-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--diff", type=float, default=6.0, help="higher drops more near-duplicates")
    a = p.parse_args()
    pack(Path(a.vault_dir).expanduser(), Path(a.out).expanduser(), a.diff)


if __name__ == "__main__":
    main()
