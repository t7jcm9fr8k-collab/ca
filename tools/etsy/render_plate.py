#!/usr/bin/env python3
"""
render_plate.py — image-plate shirt artwork, print-ready.

Companion to Design/render/render_shirt.py, which does TEXT designs only. This
one does the other half: a public-domain illustration (a Haeckel plate, a
Kuniyoshi print, an Audubon bird) turned into a shirt file.

WHY IT EXISTS, AND WHY IT IS NOT OPTIONAL
    Etsy's Creativity Standards were revised in August 2026. The language that
    permitted selling digital files of scanned vintage content was removed, and
    items produced with computerized tools must now be based on the seller's
    ORIGINAL DESIGN. Public-domain art is still usable on a physical product —
    but you have to have designed something, not resold a scan.

    So this script is the design step. Every transformation it applies is real
    work on the file, and `--report` prints exactly what it did in a sentence
    you can put in the listing description. Do the work, then describe it. Never
    the other way round.

    Separately, it fixes the biggest visual tell of an amateur POD shirt: the
    cream rectangle of aged paper printed around the artwork. Lifting the plate
    ground is both the quality win and the design labour.

WHAT IT MAKES
    4500 x 5400 px PNG, 300 DPI, transparent background — Printify's standard
    front-print file. Same canvas as render_shirt.py, deliberately.

    Two colourways every time, same as the text renderer and for the same
    reason — a file that assumes a white shirt shipped onto a black one is a
    ruined order, and that has been caught in this project once already.
        *-onlight.png   for LIGHT garments — dark caption ink
        *-ondark.png    for DARK  garments — light caption ink

    ⚠ Read the dark-garment warning under --halo before selling one. A colour
    plate with fine dark linework can vanish on black; the script tells you when
    it thinks that is the case, but only your eyes on a real mockup settle it.

USAGE
    python3 render_plate.py --src Haeckel-Cyanea-annasethe-1.jpg \\
                            --slug jellyfish-blue \\
                            --binomial "Cyanea annasethe" --year 1904

    python3 render_plate.py --src plate.jpg --slug x --no-lift    # keep ground
    python3 render_plate.py --src plate.jpg --slug x --report     # what it did
    python3 render_plate.py --src plate.jpg --slug x --halo       # dark garments

FONTS
    Same rule as render_shirt.py, and for the same licensing reason: OFL files
    in ./fonts/ are preferred, system fonts are a fallback that prints a warning
    and must not be used for anything you sell. Drop Anton-Regular.ttf and
    ArchivoBlack-Regular.ttf next to this file, or point --fonts at the existing
    Design/render/fonts directory.

DEPENDENCIES
    Pillow only. No network, no API, no numpy — same posture as the rest of the
    render tooling.
"""

import argparse
import os
import sys
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# ---------------------------------------------------------------- canvas

CANVAS = (4500, 5400)      # Printify front print, 15 x 18 in at 300 DPI.
DPI = 300                  # Verify per blueprint in Printify's Product Creator.
MARGIN = 0.92              # fraction of canvas the artwork may fill
CAPTION_RESERVE = 0.10     # fraction of height kept clear for the caption

INK = {
    "onlight": (26, 26, 26, 255),     # #1A1A1A — matches render_shirt.py
    "ondark":  (255, 255, 255, 255),
}

HERE = os.path.dirname(os.path.abspath(__file__))

FONT_CANDIDATES = {
    "caption": ["ArchivoBlack-Regular.ttf", "Archivo Black", "Arial Black", "DejaVuSans-Bold.ttf"],
}


# ---------------------------------------------------------------- fonts

def resolve(role, fontdir):
    """Prefer an OFL file we ship; fall back to a system font with a warning."""
    for name in FONT_CANDIDATES[role]:
        p = os.path.join(fontdir, name)
        if os.path.exists(p):
            return p, True
    for name in FONT_CANDIDATES[role]:
        for d in ("/usr/share/fonts", "/Library/Fonts", "/System/Library/Fonts",
                  os.path.expanduser("~/Library/Fonts")):
            for root, _, files in os.walk(d):
                if name in files:
                    return os.path.join(root, name), False
    return None, False


def font(role, size, fontdir):
    path, licensed = resolve(role, fontdir)
    if path is None:
        return ImageFont.load_default(), False
    try:
        return ImageFont.truetype(path, size), licensed
    except OSError:
        return ImageFont.load_default(), False


# ---------------------------------------------------------------- background

def _sentinel(img):
    """A colour the image does not already contain, for the flood fill."""
    used = {c for _, c in img.getcolors(maxcolors=1 << 24) or []}
    for cand in [(255, 0, 255), (0, 255, 0), (255, 255, 0), (0, 255, 255)]:
        if cand not in used:
            return cand
    return (255, 0, 255)


def _paper_colour(img):
    """Median of the four corner patches — the plate's aged-paper ground."""
    w, h = img.size
    k = max(4, min(w, h) // 40)
    px = []
    for box in [(0, 0, k, k), (w - k, 0, w, k), (0, h - k, k, h), (w - k, h - k, w, h)]:
        px.extend(img.crop(box).getdata())
    px.sort(key=lambda c: sum(c))
    return px[len(px) // 2]


def lift_background(img, thresh=42, feather=2.0, step=None,
                    key_enclosed=True, sat_max=60, val_min=185):
    """
    Remove the paper ground by flood-filling inward from the border.

    Flood fill rather than a global colour key on purpose: the light areas
    INSIDE a jellyfish bell are the same cream as the paper, and a global key
    punches holes straight through the subject. Filling only from the edges
    keeps enclosed interiors intact.

    Returns (rgba_image, coverage) where coverage is the fraction of pixels
    made transparent — a sanity number worth looking at before you print.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size
    work = rgb.copy()
    sent = _sentinel(rgb)
    paper = _paper_colour(rgb)

    if step is None:
        step = max(1, min(w, h) // 200)

    seeds = []
    for x in range(0, w, step):
        seeds += [(x, 0), (x, h - 1)]
    for y in range(0, h, step):
        seeds += [(0, y), (w - 1, y)]

    px = work.load()
    for (x, y) in seeds:
        c = px[x, y]
        if c == sent:
            continue
        # only seed where the border pixel really is paper
        if sum(abs(a - b) for a, b in zip(c, paper)) <= thresh * 3:
            ImageDraw.floodfill(work, (x, y), sent, thresh=thresh)

    # sentinel -> transparent, everything else opaque.
    # Done as a whole-image difference rather than a per-pixel loop: the loop was
    # 7.6M Python iterations on a 2300x3300 plate (~10s), which a four-layer
    # composite pays four times over. ImageChops runs in C.
    diff = ImageChops.difference(work, Image.new("RGB", (w, h), sent)).convert("L")
    mask = diff.point(lambda v: 0 if v == 0 else 255)

    # Second pass — the enclosed gaps.
    #
    # The border fill cannot reach paper that is fully surrounded by subject:
    # on a Haeckel medusa the spaces BETWEEN the tentacles are exactly that, and
    # left alone they print as opaque cream blobs on a coloured garment. This is
    # the single most visible defect in the first version of this script.
    #
    # Those gaps are paper: desaturated and bright. The subject is pigment:
    # saturated. So key on saturation and value rather than on connectivity,
    # which needs no numpy and costs one pass.
    if key_enclosed:
        hsv = rgb.convert("HSV")
        sat, val = hsv.getchannel(1), hsv.getchannel(2)
        low_sat = sat.point(lambda v: 255 if v < sat_max else 0)
        high_val = val.point(lambda v: 255 if v > val_min else 0)
        paperish = ImageChops.multiply(low_sat, high_val)
        # Drop speckle: a lone bright pixel inside the bell is a highlight, not
        # a gap. MinFilter erodes, MaxFilter grows the survivors back.
        paperish = paperish.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
        keep = paperish.point(lambda v: 0 if v > 127 else 255)
        mask = ImageChops.multiply(mask, keep)

    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))

    out = rgb.convert("RGBA")
    out.putalpha(mask)
    transparent = sum(mask.histogram()[:128])   # >half transparent counts as cleared
    return out, _cleared_fraction(transparent, w * h)


def _cleared_fraction(cleared, total):
    return cleared / float(total) if total else 0.0


# ---------------------------------------------------------------- tone

def rebuild_tones(img, black_point=12, white_point=243, gamma=0.92, saturation=1.12):
    """
    Rebuild contrast for DTG.

    Lithographic plates are scanned flat and low-contrast; printed on cotton at
    chest scale they go muddy. Pulling the black point down, the white point up
    and adding a little saturation is what makes the linework survive the
    fabric. Alpha is preserved untouched — this only touches colour.
    """
    alpha = img.getchannel("A") if img.mode == "RGBA" else None
    rgb = img.convert("RGB")

    span = max(1, white_point - black_point)
    lut = []
    for i in range(256):
        v = (i - black_point) / span
        v = 0.0 if v < 0 else (1.0 if v > 1 else v)
        lut.append(int(round((v ** gamma) * 255)))
    rgb = rgb.point(lut * 3)

    if saturation != 1.0:
        rgb = ImageEnhance.Color(rgb).enhance(saturation)

    out = rgb.convert("RGBA")
    if alpha is not None:
        out.putalpha(alpha)
    return out


def trim_to_content(img, pad=8):
    """Crop to the artwork's own bounding box so centring means what it says."""
    bbox = img.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l, t = max(0, l - pad), max(0, t - pad)
    r, b = min(img.width, r + pad), min(img.height, b + pad)
    return img.crop((l, t, r, b))


# ---------------------------------------------------------------- compose

def fit_into(art, canvas_size, margin, reserve):
    """
    Scale to fit the print area. Crop, never stretch — aspect is preserved and
    the shorter axis decides, so nothing is distorted and nothing is sliced
    mid-tendril at the bottom edge.
    """
    cw, ch = canvas_size
    avail_w = int(cw * margin)
    avail_h = int(ch * margin * (1.0 - reserve))
    scale = min(avail_w / art.width, avail_h / art.height)
    new = (max(1, int(art.width * scale)), max(1, int(art.height * scale)))
    return art.resize(new, Image.LANCZOS)


def typeset_caption(canvas, binomial, year, ink, fontdir, top_y):
    """
    A small set-framing line under the artwork: the species binomial and year.

    This is the cheapest of the transformations and it does real work — it makes
    the piece a designed series rather than a reproduction, and it is the part a
    reviewer looking for "designed by seller" can actually see.
    """
    if not binomial and not year:
        return False, True
    text = " · ".join([t for t in [binomial.upper() if binomial else None,
                                   str(year) if year else None] if t])
    draw = ImageDraw.Draw(canvas)
    size = max(28, int(canvas.width * 0.030))
    fnt, licensed = font("caption", size, fontdir)

    track = int(size * 0.16)
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + track * (len(text) - 1)
    x = (canvas.width - total) / 2.0
    for ch, w in zip(text, widths):
        draw.text((x, top_y), ch, font=fnt, fill=ink)
        x += w + track
    return True, licensed


# ---------------------------------------------------------------- render

def render(src, slug, outdir, binomial, year, fontdir,
           do_lift=True, halo=False, thresh=42, feather=2.0,
           key_enclosed=True, sat_max=60, val_min=185,
           black_point=12, white_point=243, gamma=0.92, saturation=1.12):
    art = Image.open(src)
    applied = []   # customer-facing, goes in the listing
    stats = []     # internal, never goes in the listing

    if do_lift:
        art, coverage = lift_background(art, thresh=thresh, feather=feather,
                                        key_enclosed=key_enclosed,
                                        sat_max=sat_max, val_min=val_min)
        applied.append("paper ground lifted")
        stats.append(f"{coverage:.0%} of the scan cleared")
    else:
        art = art.convert("RGBA")

    art = rebuild_tones(art, black_point, white_point, gamma, saturation)
    applied.append("tones rebuilt for fabric")

    art = trim_to_content(art)
    art = fit_into(art, CANVAS, MARGIN, CAPTION_RESERVE)
    applied.append("recomposed for the 15x18in print area")

    os.makedirs(outdir, exist_ok=True)
    results = []
    licensed_ok = True

    for way, ink in INK.items():
        canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
        x = (CANVAS[0] - art.width) // 2
        y = int(CANVAS[1] * 0.045)

        if halo and way == "ondark":
            # A soft light backing so dark linework survives a black garment.
            glow = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
            glow.paste(art, (x, y), art)
            a = glow.getchannel("A").filter(ImageFilter.GaussianBlur(28))
            backing = Image.new("RGBA", CANVAS, (255, 255, 255, 190))
            backing.putalpha(a)
            canvas = Image.alpha_composite(canvas, backing)

        canvas.paste(art, (x, y), art)

        cap_y = y + art.height + int(CANVAS[1] * 0.022)
        drew, lic = typeset_caption(canvas, binomial, year, ink, fontdir, cap_y)
        if drew:
            licensed_ok = licensed_ok and lic

        path = os.path.join(outdir, f"{slug}-{way}.png")
        canvas.save(path, "PNG", dpi=(DPI, DPI))
        results.append(path)

    if binomial or year:
        applied.append("species binomial and year typeset as a set framing")

    return results, applied, stats, licensed_ok


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="the source plate (full resolution)")
    ap.add_argument("--slug", required=True, help="output filename stem")
    ap.add_argument("--binomial", default="", help="species name for the caption")
    ap.add_argument("--year", default="", help="year for the caption")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--fonts", default=os.path.join(HERE, "fonts"))
    ap.add_argument("--no-lift", action="store_true", help="keep the paper ground")
    ap.add_argument("--halo", action="store_true",
                    help="soft light backing on the dark-garment file")
    ap.add_argument("--thresh", type=int, default=42, help="background match tolerance")
    ap.add_argument("--feather", type=float, default=2.0, help="edge softening, px")
    ap.add_argument("--black-point", type=int, default=12)
    ap.add_argument("--white-point", type=int, default=243)
    ap.add_argument("--gamma", type=float, default=0.92)
    ap.add_argument("--saturation", type=float, default=1.12)
    ap.add_argument("--no-key-enclosed", action="store_true",
                    help="skip the second pass that clears paper trapped between tentacles")
    ap.add_argument("--sat-max", type=int, default=60,
                    help="below this saturation a pixel counts as paper (0-255)")
    ap.add_argument("--val-min", type=int, default=185,
                    help="above this brightness a pixel counts as paper (0-255)")
    ap.add_argument("--preview", action="store_true", default=True,
                    help="also write a small preview on grey so the cutout is checkable")
    ap.add_argument("--report", action="store_true",
                    help="print a listing-ready sentence describing the design work")
    a = ap.parse_args()

    if not os.path.exists(a.src):
        sys.exit(f"source not found: {a.src}")

    src_img = Image.open(a.src)
    if min(src_img.size) < 1500:
        print(f"⚠ {a.src} is {src_img.width}x{src_img.height}. Under ~1500px on the "
              f"short edge goes soft at chest size. Get the full-resolution file.",
              file=sys.stderr)

    paths, applied, stats, licensed_ok = render(
        a.src, a.slug, a.out, a.binomial, a.year, a.fonts,
        do_lift=not a.no_lift, halo=a.halo, thresh=a.thresh, feather=a.feather,
        key_enclosed=not a.no_key_enclosed, sat_max=a.sat_max, val_min=a.val_min,
        black_point=a.black_point, white_point=a.white_point,
        gamma=a.gamma, saturation=a.saturation)

    for p in paths:
        print(f"wrote {p}")

    if not licensed_ok:
        print("\n⚠ FONT LICENCE: fell back to a system font. Fine for looking at, "
              "NOT fine for uploading to Printify. Put the OFL files in "
              f"{a.fonts} before you sell anything this made.", file=sys.stderr)

    if not a.halo:
        print("\nNote: the -ondark file has no backing. A plate with fine dark "
              "linework can disappear on a black garment — check it on a real "
              "mockup, or re-run with --halo.", file=sys.stderr)

    if a.preview:
        for p in paths:
            im = Image.open(p)
            bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
            prev = Image.alpha_composite(bg, im).convert("RGB")
            prev.thumbnail((500, 600), Image.LANCZOS)
            pp = p.replace(".png", "-preview.png")
            prev.save(pp)
            print(f"wrote {pp}")
        print("\nCheck the previews before printing. Grey shows you exactly what is\n"
              "transparent — look for cream left between the tentacles, and for holes\n"
              "punched through light areas inside the subject. Tune with --sat-max\n"
              "and --val-min, or --no-key-enclosed to turn the second pass off.")

    if a.report:
        print("\n--- internal, not for the listing ---")
        print("  " + ("; ".join(stats) if stats else "no stats"))
        print("\n--- listing copy: describes only what was actually applied ---")
        print("Suggested closing line:")
        year = a.year or "period"
        print(f"  Restored and reworked for fabric from the original {year} plate — "
              f"{', '.join(applied[:3])}. Made after you order it.")
        print("\nVerify each clause is true of the file you are about to upload. "
              "Copy that claims design work which did not happen is worse than no copy.")


if __name__ == "__main__":
    main()
