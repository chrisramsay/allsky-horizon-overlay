#!/usr/bin/env python3
"""
Horizon overlay for indi-allsky.

  - a thin bezel ring with azimuth ticks every 10 deg
  - each town drawn as a thin white arc with dot end caps showing its angular width
  - labels set along the curve, upright on both halves of the circle,
    automatically moved to an inner ring when they would collide

Usage:
    python3 horizon_overlay.py                      # -> horizon_overlay.png
    python3 horizon_overlay.py --preview frame.jpg  # also -> preview.png
    python3 horizon_overlay.py --cardinals          # adds N/E/S/W for calibrating ROT
    python3 horizon_overlay.py --profile profile.csv
                                  # adds a ring of bars showing measured light per
                                  # degree of azimuth (from viirs_profile.py)
"""
import argparse
import csv
import math

from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# Site and camera (matches indi-allsky config)
# --------------------------------------------------------------------------
SITE_LAT = 53.538
SITE_LON = -0.383

# Overlay size = image size AFTER crop, BEFORE IMAGE_BORDER is added
IMG_W = 3456
IMG_H = 3456
LENS_IMAGE_CIRCLE = 3316    # px diameter
LENS_FOV = 181.5            # deg
LENS_OFFSET_X = 0
LENS_OFFSET_Y = 0

ROT = 0.0                   # deg, + = clockwise on screen - CALIBRATE
EAST_LEFT = False           # matches indi-allsky cardinals with both flips on

# --------------------------------------------------------------------------
# Towns: (name, lat, lon, width_km, approx population)
# Population sets label priority (brightest towns get the outer ring).
# --------------------------------------------------------------------------
TOWNS = [
    ("Hull",         53.744, -0.333, 12.0, 267000),
    ("Grimsby",      53.567, -0.080,  8.0, 130000),   # incl. Cleethorpes
    ("Grasby",       53.530, -0.359,  0.7,    400),
    ("Caistor",      53.497, -0.316,  1.5,   2500),
    ("Market Rasen", 53.388, -0.337,  2.0,   4000),
    ("Lincoln",      53.234, -0.538,  8.0, 104000),
    ("Brigg",        53.552, -0.489,  2.0,   6000),
    ("Scunthorpe",   53.588, -0.654,  7.0,  82000),
]

# --------------------------------------------------------------------------
# Style
# --------------------------------------------------------------------------
LINE = (255, 255, 255)
BEZEL = (210, 220, 235)
TEXT = (235, 235, 235)
SHADOW = (0, 0, 0)

ARC_OFFSET = 14             # crisp arc, px outside horizon
ARC_WIDTH = 4
BEZEL_OFFSET = 4
# Label rings, tried in order: (offset from horizon px, direction of 2nd line)
# Outside the circle needs ~130 px of margin in the overlay canvas; with a
# tight crop there isn't room, so labels go inside, clear of the profile bars.
LABELS_INSIDE = True
LABEL_RINGS_OUTSIDE = [(64, +1), (-110, -1)]
LABEL_RINGS_INSIDE = [(-110, -1), (-200, -1)]
BAR_MAX = 64                # longest profile bar, px inward from horizon
BAR_GAP = 3                 # px between horizon and bar base
BAR_ALPHA = (40, 200)       # faintest .. brightest bar opacity
NAME_SIZE = 42
DIST_SIZE = 30
LABEL_PAD_DEG = 2.0         # minimum angular gap between labels
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ---------------------------------------------------------------- geometry --
CX = IMG_W / 2 + LENS_OFFSET_X
CY = IMG_H / 2 + LENS_OFFSET_Y
R_H = (LENS_IMAGE_CIRCLE / 2) * 90.0 / (LENS_FOV / 2)   # horizon radius


def bearing_distance(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    brg = (math.degrees(math.atan2(x, y)) + 360) % 360
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return brg, 6371.0 * math.acos(max(-1.0, min(1.0, c)))


def screen_angle(az):
    """Azimuth -> screen angle (deg, clockwise from straight up)."""
    phi = (-(az) if EAST_LEFT else az) + ROT
    return phi % 360


def xy(phi, r):
    a = math.radians(phi)
    return CX + r * math.sin(a), CY - r * math.cos(a)


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


# ------------------------------------------------------------ curved text --
def text_span_deg(text, fnt, r):
    return math.degrees(fnt.getlength(text) / r)


def draw_curved_text(layer, text, fnt, phi_c, r, colour):
    """Draw text centred on screen angle phi_c along radius r, kept upright."""
    total = text_span_deg(text, fnt, r)
    top_half = math.cos(math.radians(phi_c)) >= 0
    # top half: read clockwise; bottom half: read anticlockwise and flip
    direction = 1 if top_half else -1
    phi = phi_c - direction * total / 2
    for ch in text:
        adv = math.degrees(fnt.getlength(ch) / r)
        mid = phi + direction * adv / 2
        if ch.strip():
            l, t, rr, b = fnt.getbbox(ch, stroke_width=3)
            w, h = rr - l + 8, b - t + 8
            tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text((4 - l, 4 - t), ch, font=fnt, fill=colour + (255,),
                                      stroke_width=3, stroke_fill=SHADOW + (200,))
            rot = mid if top_half else mid + 180
            tile = tile.rotate(-rot, resample=Image.BICUBIC, expand=True)
            x, y = xy(mid, r)
            layer.alpha_composite(tile, (int(x - tile.width / 2), int(y - tile.height / 2)))
        phi += direction * adv


# ------------------------------------------------------------------ build --
def build_overlay(cardinals=False, profile=None):
    f_name, f_dist = font(FONT_BOLD, NAME_SIZE), font(FONT_REG, DIST_SIZE)

    towns = []
    for name, lat, lon, width_km, pop in TOWNS:
        brg, dist = bearing_distance(SITE_LAT, SITE_LON, lat, lon)
        half = max(1.0, math.degrees(math.atan((width_km / 2) / max(dist, 0.1))))
        impact = pop / max(dist, 1.0) ** 2.5
        towns.append(dict(name=name, brg=brg, dist=dist, half=half, impact=impact,
                          phi=screen_angle(brg)))

    img = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # --- light-pollution profile bars ----------------------------------
    if profile:
        r0 = R_H - BAR_GAP
        for az, v in profile.items():
            if v <= 0.01:
                continue
            r1 = r0 - BAR_MAX * v
            a = int(BAR_ALPHA[0] + v * (BAR_ALPHA[1] - BAR_ALPHA[0]))
            p0, p1 = screen_angle(az + 0.08), screen_angle(az + 0.92)
            d.polygon([xy(p0, r0), xy(p1, r0), xy(p1, r1), xy(p0, r1)],
                      fill=LINE + (a,))

    # --- bezel ------------------------------------------------------------
    rb = R_H + BEZEL_OFFSET
    d.ellipse([CX - rb, CY - rb, CX + rb, CY + rb], outline=BEZEL + (90,), width=2)
    for az in range(0, 360, 10):
        length = 22 if az % 30 == 0 else 11
        phi = screen_angle(az)
        d.line([xy(phi, rb), xy(phi, rb + length)], fill=BEZEL + (110,), width=2)

    # --- crisp arcs with end caps ----------------------------------------
    ra = R_H + ARC_OFFSET
    for t in towns:
        steps = max(12, int(t["half"] * 4))
        pts = [xy(t["phi"] - t["half"] + 2 * t["half"] * i / steps, ra) for i in range(steps + 1)]
        d.line(pts, fill=LINE + (255,), width=ARC_WIDTH, joint="curve")
        for px, py in (pts[0], pts[-1]):
            d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=LINE + (255,))

    # --- labels with collision avoidance ---------------------------------
    rings = LABEL_RINGS_INSIDE if LABELS_INSIDE else LABEL_RINGS_OUTSIDE
    placed = []   # (ring index, centre_deg, span_deg)

    def clashes(ring, centre, span):
        for rg, c, sp in placed:
            gap = abs((centre - c + 180) % 360 - 180)
            if rg == ring and gap < (span + sp) / 2:
                return True
        return False

    print(f"Horizon radius {R_H:.0f}px  ROT {ROT}°  canvas {IMG_W}x{IMG_H}")
    print(f"{'Town':13s} {'Bearing':>7s} {'Dist':>7s} {'Span':>6s}  Ring")
    # brightest towns get first pick of the first ring
    for t in sorted(towns, key=lambda t: -t["impact"]):
        dist_txt = f"{t['dist']:.1f} km" if t["dist"] < 5 else f"{t['dist']:.0f} km"
        ring = len(rings) - 1
        for i, (base, _) in enumerate(rings):
            r = R_H + base
            span = max(text_span_deg(t["name"], f_name, r),
                       text_span_deg(dist_txt, f_dist, r)) + LABEL_PAD_DEG
            if not clashes(i, t["phi"], span):
                ring = i
                break
        base, sign = rings[ring]
        r = R_H + base
        span = max(text_span_deg(t["name"], f_name, r),
                   text_span_deg(dist_txt, f_dist, r)) + LABEL_PAD_DEG
        placed.append((ring, t["phi"], span))

        # the name is always the upper line as you read it
        top = math.cos(math.radians(t["phi"])) >= 0
        near, far = r, r + sign * 40
        outward_second = sign > 0
        if outward_second:
            r_name, r_dist = (far, near) if top else (near, far)
        else:
            r_name, r_dist = (near, far) if top else (far, near)

        draw_curved_text(img, t["name"], f_name, t["phi"], r_name, TEXT)
        draw_curved_text(img, dist_txt, f_dist, t["phi"], r_dist, TEXT)
        print(f"{t['name']:13s} {t['brg']:6.1f}° {t['dist']:5.1f}km {2*t['half']:5.1f}°  {ring + 1}")

    if cardinals:
        for lab, az in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            phi = screen_angle(az)
            d.line([xy(phi, R_H - 70), xy(phi, R_H)], fill=(80, 200, 255, 230), width=6)
            draw_curved_text(img, lab, f_name, phi, R_H - 110, (80, 200, 255))

    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="horizon_overlay.png")
    ap.add_argument("--preview", metavar="FRAME")
    ap.add_argument("--cardinals", action="store_true")
    ap.add_argument("--profile", metavar="CSV",
                    help="profile.csv from viirs_profile.py")
    args = ap.parse_args()

    profile = None
    if args.profile:
        with open(args.profile) as f:
            profile = {int(r["azimuth_deg"]): float(r["normalised"]) for r in csv.DictReader(f)}

    overlay = build_overlay(args.cardinals, profile)
    overlay.save(args.out)
    print(f"Wrote {args.out}")

    if args.preview:
        frame = Image.open(args.preview).convert("RGBA")
        if frame.size != overlay.size:
            overlay = overlay.resize(frame.size, Image.LANCZOS)
        Image.alpha_composite(frame, overlay).convert("RGB").save("preview.png")
        print("Wrote preview.png")


if __name__ == "__main__":
    main()
