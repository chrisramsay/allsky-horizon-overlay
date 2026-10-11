#!/usr/bin/env python3
"""
Measure the fisheye image circle in a real allsky frame.

Scans outwards along 720 rays to find the rim of the lit disc, then fits a
circle with outlier rejection, so text labels, overlay graphics and a dim
section of the rim don't drag the result. Works best on a bright daytime frame.

Usage:
    python3 find_circle.py frame.jpg
    python3 find_circle.py frame.jpg --threshold 25   # if the rim is dim
"""
import argparse

import numpy as np
from PIL import Image, ImageDraw


def fit_circle(x, y):
    """Algebraic (Kasa) least-squares circle fit."""
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x ** 2 + y ** 2
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0] / 2, c[1] / 2
    r = np.sqrt(c[2] + cx ** 2 + cy ** 2)
    return cx, cy, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--threshold", type=int, default=25,
                    help="brightness (0-255) counted as inside the circle")
    args = ap.parse_args()

    a = np.asarray(Image.open(args.frame).convert("L"), dtype=np.int16)
    h, w = a.shape
    mask = a > args.threshold

    # Radial scan: from near the frame centre, walk outwards along 720 rays
    # and record where the lit disc ends (first run of GAP unlit pixels).
    # Text and overlay graphics beyond a dark gap are never reached.
    GAP = 25
    cx0, cy0 = w / 2, h / 2
    rmax = int(np.hypot(w, h) / 2)
    rr = np.arange(int(min(w, h) * 0.2), rmax)
    xs, ys = [], []
    for ang in np.linspace(0, 2 * np.pi, 720, endpoint=False):
        px = np.round(cx0 + rr * np.cos(ang)).astype(int)
        py = np.round(cy0 + rr * np.sin(ang)).astype(int)
        ok = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        lit = np.zeros(rr.size, bool)
        lit[ok] = mask[py[ok], px[ok]]
        dark = ~lit
        # index of first window of GAP consecutive dark pixels
        run = np.convolve(dark.astype(int), np.ones(GAP, int), "valid")
        hits = np.nonzero(run == GAP)[0]
        if hits.size and hits[0] > 0 and ok[hits[0]]:
            i = hits[0] - 1
            xs.append(px[i]); ys.append(py[i])
    xs, ys = np.array(xs, float), np.array(ys, float)
    if xs.size < 50:
        raise SystemExit("No disc edge found - try a brighter frame or lower --threshold")

    # robust fit: drop points more than 3 MAD from the circle, repeat
    keep = np.ones(xs.size, bool)
    for _ in range(8):
        cx, cy, r = fit_circle(xs[keep], ys[keep])
        resid = np.hypot(xs - cx, ys - cy) - r
        mad = np.median(np.abs(resid[keep] - np.median(resid[keep]))) + 0.5
        new_keep = np.abs(resid) < 3 * 1.4826 * mad
        if new_keep.sum() < 50 or (new_keep == keep).all():
            break
        keep = new_keep
    cx, cy, r = fit_circle(xs[keep], ys[keep])
    used = 100 * keep.sum() / xs.size

    print(f"Frame size:      {w} x {h}")
    print(f"Centre:          ({cx:.0f}, {cy:.0f})")
    print(f"Diameter:        {2 * r:.0f} px")
    print(f"Rim points:      {keep.sum()} of {xs.size} rays used ({used:.0f}%)")
    print()
    print("Copy into horizon_overlay_v2.py:")
    print(f"  LENS_IMAGE_CIRCLE = {2 * r:.0f}")
    print(f"  LENS_OFFSET_X = {cx - w / 2:.0f}")
    print(f"  LENS_OFFSET_Y = {cy - h / 2:.0f}")

    chk = Image.open(args.frame).convert("RGB")
    d = ImageDraw.Draw(chk)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 0, 0), width=6)
    d.line([cx - 40, cy, cx + 40, cy], fill=(255, 0, 0), width=6)
    d.line([cx, cy - 40, cx, cy + 40], fill=(255, 0, 0), width=6)
    for px, py in zip(xs[keep][::4], ys[keep][::4]):
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(0, 255, 0))
    chk.save("circle_check.png")
    print("\nWrote circle_check.png - red = fitted circle, green = edge points used.")


if __name__ == "__main__":
    main()
