#!/usr/bin/env python3
"""
Build a horizon light-pollution profile from VIIRS night-lights data.

For every pixel within RADIUS_KM of the site, take its radiance, weight it by
distance^-2.5 (Walker's law for sky glow), and add it to the 1-degree azimuth
bin it lies in. The result is 360 numbers: how much artificial light reaches
your sky from each direction.

Input:  a VIIRS annual composite GeoTIFF (EOG "VNL" average_masked layer),
        ideally pre-cropped to the area around the site - see README below.
Output: profile.csv  (azimuth_deg, raw, smoothed, normalised 0..1)
        a ranked list of the brightest directions, printed to the terminal

README - getting the data
-------------------------
1. Register (free) at the Earth Observation Group, Colorado School of Mines,
   and download the latest annual VNL GeoTIFF ("average_masked" layer).
   It is a large global file, usually gzipped: gunzip it first.
2. Crop it to your area so it is small and quick to work with:

     gdal_translate -projwin -1.35 54.15 0.60 52.95 \\
         VNL_..._average_masked.dat.tif lincs_viirs.tif

   (-projwin is west north east south in degrees; this box covers
   ~60 km around Searby with margin.)
3. pip install rasterio numpy
4. python3 viirs_profile.py lincs_viirs.tif

Site location and the settings below come from site.toml (needs
allsky_site.py and site.toml / site.example.toml alongside this script).

Run it wherever is convenient (desktop or OMV); only profile.csv needs to go
to the Pi for the overlay script.
"""
import argparse
import csv
import math

import numpy as np
import rasterio
from rasterio.windows import from_bounds

import allsky_site  # site.toml - see site.example.toml

_CFG = allsky_site.load()
SITE_LAT = _CFG["site"]["latitude"]
SITE_LON = _CFG["site"]["longitude"]
RADIUS_KM = float(_CFG["viirs"]["radius_km"])     # how far out to count light
MIN_KM = float(_CFG["viirs"]["min_km"])           # ignore your own lights
WALKER_EXP = float(_CFG["viirs"]["walker_exp"])   # sky glow ~ light * distance^-2.5
SMOOTH_DEG = int(_CFG["viirs"]["smooth_deg"])     # moving-average width (odd, 1 = off)
EARTH_KM = 6371.0


def load_window(path):
    """Read only the part of the raster within RADIUS_KM (+margin) of the site."""
    dlat = math.degrees((RADIUS_KM + 5) / EARTH_KM)
    dlon = dlat / math.cos(math.radians(SITE_LAT))
    with rasterio.open(path) as src:
        win = from_bounds(SITE_LON - dlon, SITE_LAT - dlat,
                          SITE_LON + dlon, SITE_LAT + dlat, src.transform)
        win = win.round_offsets().round_lengths()
        data = src.read(1, window=win, masked=True).astype("float64").filled(0.0)
        transform = src.window_transform(win)
        if src.crs and src.crs.to_epsg() != 4326:
            raise SystemExit(f"Expected EPSG:4326 (lat/lon) raster, got {src.crs}")
    return data, transform


def profile(data, transform):
    rows, cols = np.indices(data.shape)
    # pixel centres -> lon/lat
    lon = transform.c + (cols + 0.5) * transform.a + (rows + 0.5) * transform.b
    lat = transform.f + (cols + 0.5) * transform.d + (rows + 0.5) * transform.e

    p1, p2 = math.radians(SITE_LAT), np.radians(lat)
    dl = np.radians(lon - SITE_LON)
    x = np.sin(dl) * np.cos(p2)
    y = math.cos(p1) * np.sin(p2) - math.sin(p1) * np.cos(p2) * np.cos(dl)
    brg = (np.degrees(np.arctan2(x, y)) + 360.0) % 360.0
    c = math.sin(p1) * np.sin(p2) + math.cos(p1) * np.cos(p2) * np.cos(dl)
    dist = EARTH_KM * np.arccos(np.clip(c, -1.0, 1.0))

    rad = np.where(data > 0, data, 0.0)          # drop negative/no-data noise
    keep = (dist >= MIN_KM) & (dist <= RADIUS_KM) & (rad > 0)
    weight = rad[keep] * dist[keep] ** -WALKER_EXP
    bins = np.floor(brg[keep]).astype(int) % 360
    raw = np.bincount(bins, weights=weight, minlength=360)

    if SMOOTH_DEG > 1:
        k = np.ones(SMOOTH_DEG) / SMOOTH_DEG
        padded = np.concatenate([raw[-SMOOTH_DEG:], raw, raw[:SMOOTH_DEG]])
        smooth = np.convolve(padded, k, mode="same")[SMOOTH_DEG:-SMOOTH_DEG]
    else:
        smooth = raw.copy()

    # log scale for display: sky glow spans orders of magnitude
    pos = smooth[smooth > 0]
    lo = np.percentile(pos, 25) if pos.size else 1.0   # quietest quarter = no bar
    hi = smooth.max() if smooth.max() > 0 else 1.0
    norm = np.clip((np.log10(np.maximum(smooth, lo)) - math.log10(lo)) /
                   max(math.log10(hi) - math.log10(lo), 1e-9), 0, 1)
    return raw, smooth, norm


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("geotiff")
    ap.add_argument("--out", default="profile.csv")
    args = ap.parse_args()

    data, transform = load_window(args.geotiff)
    print(f"Window {data.shape[1]}x{data.shape[0]} px, radius {RADIUS_KM:.0f} km")
    raw, smooth, norm = profile(data, transform)

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["azimuth_deg", "raw", "smoothed", "normalised"])
        for az in range(360):
            w.writerow([az, f"{raw[az]:.6g}", f"{smooth[az]:.6g}", f"{norm[az]:.4f}"])
    print(f"Wrote {args.out}")

    # brightest directions, merged into peaks at least 10 deg apart
    order = np.argsort(-smooth)
    peaks = []
    for az in order:
        if all(abs((az - p + 180) % 360 - 180) >= 10 for p in peaks):
            peaks.append(int(az))
        if len(peaks) == 8:
            break
    print("\nBrightest directions:")
    for az in peaks:
        print(f"  {az:3d}°   relative {norm[az]:.2f}")


if __name__ == "__main__":
    main()
