#!/usr/bin/env python3
"""
Generate an indi-allsky detection mask (DETECT_MASK).

White = use this area, black = ignore it. indi-allsky uses the mask for star
and meteor detection and, when set, for measuring image brightness (ADU), so
excluding the low horizon stops streetlights, house lights and glowing low
cloud from dragging the exposure about.

The mask is a disc of sky above MIN_ALT degrees, with optional extra
exclusions for obstructions (house, trees) in particular directions.

Usage:
    python3 detection_mask.py                       # -> detection_mask.png
    python3 detection_mask.py --preview frame.jpg   # also -> mask_preview.png
                                                    #   (rough visual check only - the
                                                    #    saved frames are cropped, the
                                                    #    mask is not)
                                                    #   (ignored area tinted red)

Then copy detection_mask.png to /var/lib/indi-allsky/ and set DETECT_MASK.
"""
import argparse
import math

from PIL import Image, ImageDraw

# --------------------------------------------------------------------------
# Geometry and mask settings come from site.toml (see site.example.toml).
#
# IMPORTANT: unlike the logo overlay, the detection mask must match the FULL,
# UNCROPPED sensor frame ([frame.full], 3552 x 3552 here). indi-allsky uses it
# for the SQM calculation before IMAGE_CROP_ROI is applied; a mask at the
# cropped size makes the image worker crash on every frame with
#   cv2.error: (-209:Sizes of input arguments do not match) ... 'binary_op'
#
# In the uncropped frame the circle centre is ~65 px from the middle, but the
# direction depends on whether indi-allsky applies its flips before or after
# this stage, so [frame.full] offsets are left at 0. The cut-off disc (radius
# ~1279 px at 20 deg) sits well inside the 1658 px sky circle, so a 65 px
# error doesn't matter for metering or SQM.
#
# SECTORS are NOT YET VERIFIED: if the mask is applied before the flips (both
# H and V = a 180 deg rotation) they land on the opposite side of the sky, and
# rot would need +180. Test before relying on them.
# --------------------------------------------------------------------------
import allsky_site  # noqa: E402

_CFG = allsky_site.load()
IMG_W = _CFG["frame"]["full"]["width"]
IMG_H = _CFG["frame"]["full"]["height"]
LENS_OFFSET_X = _CFG["frame"]["full"]["offset_x"]
LENS_OFFSET_Y = _CFG["frame"]["full"]["offset_y"]
LENS_IMAGE_CIRCLE = _CFG["lens"]["image_circle"]
LENS_FOV = _CFG["lens"]["fov"]
ROT = _CFG["orientation"]["rot"]
EAST_LEFT = _CFG["orientation"]["east_left"]
MIN_ALT = float(_CFG["mask"]["min_alt"])
SECTORS = [tuple(x) for x in _CFG["mask"].get("sectors", [])]


CX = IMG_W / 2 + LENS_OFFSET_X
CY = IMG_H / 2 + LENS_OFFSET_Y
R_H = (LENS_IMAGE_CIRCLE / 2) * 90.0 / (LENS_FOV / 2)   # horizon radius, px


def alt_to_r(alt):
    """Equidistant fisheye: radius is proportional to zenith angle."""
    return R_H * (90.0 - alt) / 90.0


def screen_angle(az):
    return ((-(az) if EAST_LEFT else az) + ROT) % 360


def xy(phi, r):
    a = math.radians(phi)
    return CX + r * math.sin(a), CY - r * math.cos(a)


def build_mask():
    mask = Image.new("L", (IMG_W, IMG_H), 0)
    d = ImageDraw.Draw(mask)

    r = alt_to_r(MIN_ALT)
    d.ellipse([CX - r, CY - r, CX + r, CY + r], fill=255)

    for az_from, az_to, alt in SECTORS:
        span = (az_to - az_from) % 360 or 360
        r_in, r_out = alt_to_r(alt), alt_to_r(MIN_ALT) + 2
        steps = max(8, int(span * 2))
        outer = [xy(screen_angle(az_from + span * i / steps), r_out) for i in range(steps + 1)]
        inner = [xy(screen_angle(az_from + span * i / steps), r_in) for i in range(steps, -1, -1)]
        d.polygon(outer + inner, fill=0)

    return mask


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="detection_mask.png")
    ap.add_argument("--preview", metavar="FRAME",
                    help="tint the ignored area red on a real frame -> mask_preview.png")
    args = ap.parse_args()

    mask = build_mask()
    mask.save(args.out)
    kept = sum(mask.histogram()[128:]) / (IMG_W * IMG_H) * 100
    print(f"Horizon radius {R_H:.0f}px, cut-off radius {alt_to_r(MIN_ALT):.0f}px "
          f"({MIN_ALT:.0f} deg), {len(SECTORS)} extra sector(s)")
    print(f"Wrote {args.out} ({IMG_W}x{IMG_H}, {kept:.0f}% of frame kept)")

    if args.preview:
        frame = Image.open(args.preview).convert("RGB")
        m = mask
        if frame.size != mask.size:
            # saved frames are cropped (+ border); the mask is full-sensor size.
            # Centre one on the other - approximate, offsets not applied.
            pad = Image.new("L", frame.size, 0)
            pad.paste(mask, ((frame.width - IMG_W) // 2, (frame.height - IMG_H) // 2))
            m = pad
        red = Image.new("RGB", frame.size, (255, 0, 0))
        tinted = Image.blend(frame, red, 0.45)
        Image.composite(frame, tinted, m).save("mask_preview.png")
        print("Wrote mask_preview.png - red = ignored")


if __name__ == "__main__":
    main()
