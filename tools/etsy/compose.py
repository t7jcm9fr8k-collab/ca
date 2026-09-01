#!/usr/bin/env python3
"""
compose.py — composite public-domain plates into one original shirt design.

The third tool in the pipeline. `render_shirt.py` sets type; `render_plate.py`
prepares a single plate; this one combines several into a composition that is
the seller's own work.

WHY COMPOSITES
    Two reasons, and the second is the one that matters commercially.

    Policy: Etsy's August 2026 Creativity Standards require items made with
    computerized tools to be based on the seller's ORIGINAL DESIGN. A single
    plate printed as-is is the case you have to defend. A composition of several
    sources, arranged and colour-unified by you, is not.

    Market: a reproduction competes with every other shop selling the same
    scan. A composition competes with nobody, because it did not exist before.

THE THING THAT MAKES OR BREAKS A COMPOSITE
    Palette harmonisation, and it is not optional.

    A Vesalius skull is brown ink on cream. A Redoute rose is full colour. A
    Piranesi etching is grey line. Stack them raw and you get a ransom note —
    three different papers, three different inks, obviously three different
    scans. Mapping every layer through ONE ink palette is what turns them into a
    single drawing. That is `map_to_ink`, and it is the most important function
    in this file.

    It works the way a real print separation works: read each source as ink
    DENSITY rather than as colour, then re-lay that density in your own ink.
    Dark areas of the source become opaque ink; light areas become nothing.

USAGE
    python3 compose.py --recipe recipes/orchid-skull.json --report
    python3 compose.py --recipe recipes/orchid-skull.json --draft   # fast, small
    python3 compose.py --list-recipes

WHAT IT WRITES
    out/<id>-onlight.png     4500x5400 @300 DPI, transparent, for LIGHT garments
    out/<id>-ondark.png      same, inks flipped, for DARK garments
    out/<id>-*-preview.png   small, composited on grey — LOOK AT THESE
    out/<id>-silhouette.png  flattened to solid black, the arm's-length test

PROVENANCE IS ENFORCED, NOT REMEMBERED
    Every layer must carry a source URL, a licence string and a traced date. A
    recipe missing any of them refuses to render. This is `Etsy-Art/SOURCES.md`'s
    rule — "No entry, no listing" — moved from a habit into the code.

DEPENDENCIES
    Pillow only. No network, no API, no numpy. Reuses render_plate.py.
"""

import argparse
import glob
import json
import os
import sys
from PIL import Image, ImageChops, ImageFilter, ImageOps

from render_plate import lift_background, trim_to_content

HERE = os.path.dirname(os.path.abspath(__file__))

CANVAS = (4500, 5400)      # Printify front print, 15 x 18 in at 300 DPI
DPI = 300
DRAFT_DIVISOR = 5          # --draft renders at 1/5 scale for fast iteration
MIN_SOURCE_PX = 1500       # short edge; below this a plate goes soft at chest size

REQUIRED_PROVENANCE = ("url", "licence", "traced")

# Licence strings that are fine on merchandise. Anything else stops the render —
# CC-BY-SA in particular is a share-alike trap on a product you sell.
LICENCE_ALLOW = ("public domain", "pd", "cc0", "no known copyright")
LICENCE_DENY = ("cc-by-sa", "by-sa", "share-alike", "sharealike", "noncommercial",
                "non-commercial", "nc", "nd", "no-derivatives")


# ---------------------------------------------------------------- ink

def _levels_from(lum, mask, lo_pct=0.02, hi_pct=0.98):
    """
    Find the luminance range a source actually occupies, ignoring its cutout.

    Measured over the OPAQUE region only. Measuring the whole frame would let
    the transparent background — which grayscale() reports as black — drag the
    floor to 0 and flatten everything.
    """
    hist = lum.histogram(mask) if mask is not None else lum.histogram()
    total = sum(hist)
    if not total:
        return 0, 255
    lo_target, hi_target = total * lo_pct, total * hi_pct
    run, lo, hi = 0, 0, 255
    for i, n in enumerate(hist):
        run += n
        if run >= lo_target:
            lo = i
            break
    run = 0
    for i, n in enumerate(hist):
        run += n
        if run >= hi_target:
            hi = i
            break
    return (lo, hi) if hi > lo else (0, 255)


def map_to_ink(img, ink, gamma=1.0, floor=None, ceil=None, autolevel=True):
    """
    Re-read a source as ink density and lay it back down in one colour.

    This is what unifies a brown engraving and a colour lithograph into the same
    drawing. Luminance becomes alpha: dark source = dense ink, light source =
    nothing. The RGB is flat — the layer's own colours are deliberately
    discarded, because keeping them is what makes a composite look like a
    collage.

    AUTO-LEVELLING IS ON BY DEFAULT AND MATTERS.
        A colour lithograph's subject sits at MID luminance, not dark. Mapped
        linearly it comes out as faint pencil — which is exactly what the first
        version of this function did to a Haeckel plate, and it was only visible
        by looking at the render. Stretching each source's own 2-98 percentile
        range to full density is what restores the linework, and it also means a
        pale plate and a heavy engraving arrive at comparable weight instead of
        one bullying the other.

    gamma > 1 thins the ink, gamma < 1 thickens it. Explicit floor/ceil override
    the automatic range when a source needs hand-holding.
    """
    lum = ImageOps.grayscale(img.convert("RGB"))
    alpha = img.getchannel("A") if img.mode == "RGBA" else None

    if autolevel and (floor is None or ceil is None):
        mask = alpha.point(lambda v: 255 if v > 8 else 0) if alpha is not None else None
        auto_lo, auto_hi = _levels_from(lum, mask)
        floor = auto_lo if floor is None else floor
        ceil = auto_hi if ceil is None else ceil
    floor = 0 if floor is None else floor
    ceil = 255 if ceil is None else ceil

    span = max(1, ceil - floor)
    lut = []
    for i in range(256):
        v = (i - floor) / span
        v = 0.0 if v < 0 else (1.0 if v > 1 else v)
        lut.append(int(round((1.0 - v) ** gamma * 255)))   # invert: dark -> opaque
    density = lum.point(lut)

    if alpha is not None:
        # Respect a cutout already made by lift_background.
        density = ImageChops.multiply(density, alpha)

    out = Image.new("RGBA", img.size, tuple(ink) + (255,))
    out.putalpha(density)
    return out


def parse_hex(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- layers

def check_provenance(recipe):
    """Refuse to render anything whose sources are not traced and cleared."""
    problems = []
    for i, layer in enumerate(recipe.get("layers", [])):
        p = layer.get("provenance") or {}
        name = layer.get("source", f"layer {i}")
        for field in REQUIRED_PROVENANCE:
            if not str(p.get(field, "")).strip():
                problems.append(f"layer {i} ({name}): provenance.{field} is empty")
        lic = str(p.get("licence", "")).lower()
        if lic:
            if any(bad in lic for bad in LICENCE_DENY):
                problems.append(
                    f"layer {i} ({name}): licence '{p['licence']}' is not usable on "
                    f"merchandise")
            elif not any(ok in lic for ok in LICENCE_ALLOW):
                problems.append(
                    f"layer {i} ({name}): licence '{p['licence']}' is not recognised "
                    f"as merchandise-safe — check the file page and use an explicit "
                    f"'public domain' or 'CC0' string if it is")
    return problems


def place(layer_img, canvas_size, transform):
    """Scale, rotate and position one layer on the canvas."""
    cw, ch = canvas_size
    t = transform or {}

    if t.get("flip"):
        layer_img = ImageOps.mirror(layer_img)

    frac = float(t.get("scale", 0.8))          # fraction of canvas width
    target_w = max(1, int(cw * frac))
    ratio = target_w / layer_img.width
    layer_img = layer_img.resize(
        (target_w, max(1, int(layer_img.height * ratio))), Image.LANCZOS)

    rot = float(t.get("rotate", 0))
    if rot:
        layer_img = layer_img.rotate(rot, resample=Image.BICUBIC, expand=True)

    ox, oy = t.get("offset", [0.0, 0.0])       # fractions of canvas, from centre
    x = int((cw - layer_img.width) / 2 + ox * cw)
    y = int((ch - layer_img.height) / 2 + oy * ch)

    slot = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    slot.paste(layer_img, (x, y), layer_img)
    return slot


def apply_mask(slot, built, spec):
    """
    Mask one layer against another already-built layer.

    This is what makes flowers pass THROUGH an eye socket rather than sit on top
    of it: mask the flower layer by the inverse of the skull's alpha, and the
    stems disappear exactly where bone would occlude them.
    """
    if not spec:
        return slot
    idx = spec.get("from_layer")
    if idx is None or idx >= len(built) or built[idx] is None:
        return slot
    m = built[idx].getchannel("A")
    if spec.get("invert", False):
        m = ImageChops.invert(m)
    if spec.get("feather"):
        m = m.filter(ImageFilter.GaussianBlur(float(spec["feather"])))
    a = ImageChops.multiply(slot.getchannel("A"), m)
    out = slot.copy()
    out.putalpha(a)
    return out


# ---------------------------------------------------------------- compose

def build(recipe, root, canvas_size, draft=False):
    """Render every layer and stack them. Returns (composite, notes)."""
    notes = []
    built = []
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

    palette = recipe.get("palette", {})
    inks = {k: parse_hex(v) for k, v in palette.get("inks", {}).items()}
    if not inks:
        inks = {"ink0": (26, 26, 26)}

    for i, layer in enumerate(recipe["layers"]):
        src = os.path.join(root, layer["source"])
        if not os.path.exists(src):
            built.append(None)
            notes.append(f"layer {i}: MISSING {layer['source']}")
            continue

        img = Image.open(src)
        if min(img.size) < MIN_SOURCE_PX:
            notes.append(f"layer {i}: SOFT — {layer['source']} is "
                         f"{img.width}x{img.height}; under {MIN_SOURCE_PX}px on the "
                         f"short edge goes soft at chest size")
            print(f"⚠ layer {i}: {layer['source']} is {img.width}x{img.height} — "
                  f"too small to print sharply. Get the full-resolution file.",
                  file=sys.stderr)

        lift = layer.get("lift") or {}
        if lift.get("enabled", True):
            img, cleared = lift_background(
                img,
                thresh=lift.get("thresh", 42),
                feather=lift.get("feather", 2.0),
                key_enclosed=lift.get("key_enclosed", True),
                sat_max=lift.get("sat_max", 60),
                val_min=lift.get("val_min", 185))
            notes.append(f"layer {i}: ground lifted ({cleared:.0%})")
            img = trim_to_content(img)

        ink_key = layer.get("ink", "ink0")
        ink = inks.get(ink_key, list(inks.values())[0])
        img = map_to_ink(img, ink,
                         gamma=float(layer.get("gamma", 1.0)),
                         floor=layer.get("floor"),
                         ceil=layer.get("ceil"),
                         autolevel=layer.get("autolevel", True))

        slot = place(img, canvas_size, layer.get("transform"))
        slot = apply_mask(slot, built, layer.get("mask"))

        op = float(layer.get("opacity", 1.0))
        if op < 1.0:
            a = slot.getchannel("A").point(lambda v: int(v * op))
            slot.putalpha(a)

        built.append(slot)
        canvas = Image.alpha_composite(canvas, slot)

    notes.append(f"{len([b for b in built if b is not None])} sources composited "
                 f"into one design")
    notes.append("unified to a single ink palette")
    return canvas, notes


def silhouette(img):
    """
    The arm's-length test, as a number.

    WHERE-TO-LOOK.md sets the criterion — hard edges, few colours, a clear
    silhouette from across a room. Flatten everything to solid black and the
    shape either reads or it does not. Coverage under ~8% is a design that
    disappears on a shirt; over ~55% is a solid slab that costs ink and cracks.
    """
    a = img.getchannel("A").point(lambda v: 255 if v > 96 else 0)
    proof = Image.new("RGBA", img.size, (255, 255, 255, 255))
    black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    black.putalpha(a)
    proof = Image.alpha_composite(proof, black)
    coverage = sum(a.histogram()[128:]) / float(img.width * img.height)
    return proof.convert("RGB"), coverage


def invert_inks(img):
    """The dark-garment file: same density, inverted ink colour."""
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    out = ImageOps.invert(rgb).convert("RGBA")
    out.putalpha(a)
    return out


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recipe", help="path to a recipe JSON")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--sources", default=os.path.join(HERE, "sources"),
                    help="root the recipe's source paths resolve against")
    ap.add_argument("--draft", action="store_true",
                    help=f"render at 1/{DRAFT_DIVISOR} scale for fast iteration")
    ap.add_argument("--report", action="store_true",
                    help="print listing-ready copy for the work actually applied")
    ap.add_argument("--list-recipes", action="store_true")
    a = ap.parse_args()

    rdir = os.path.join(HERE, "recipes")
    if a.list_recipes:
        for f in sorted(glob.glob(os.path.join(rdir, "*.json"))):
            try:
                r = json.load(open(f))
                ready = "ready" if not check_provenance(r) else "BLOCKED — provenance"
                print(f"{os.path.basename(f):<28} {r.get('title','?'):<24} {ready}")
            except Exception as e:
                print(f"{os.path.basename(f):<28} UNREADABLE: {e}")
        return

    if not a.recipe:
        sys.exit("need --recipe (or --list-recipes)")
    recipe = json.load(open(a.recipe))

    problems = check_provenance(recipe)
    if problems:
        print("REFUSING TO RENDER — provenance incomplete:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print("\nEvery source needs a URL, a licence and a traced date before it "
              "goes on a shirt. That is the SOURCES.md rule; this enforces it.",
              file=sys.stderr)
        sys.exit(2)

    size = CANVAS if not a.draft else (CANVAS[0] // DRAFT_DIVISOR,
                                       CANVAS[1] // DRAFT_DIVISOR)
    art, notes = build(recipe, a.sources, size, draft=a.draft)

    os.makedirs(a.out, exist_ok=True)
    rid = recipe.get("id", "composite")

    onlight = art
    ondark = invert_inks(art)
    for way, im in (("onlight", onlight), ("ondark", ondark)):
        p = os.path.join(a.out, f"{rid}-{way}.png")
        im.save(p, "PNG", dpi=(DPI, DPI))
        print(f"wrote {p}")

        bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
        prev = Image.alpha_composite(bg, im).convert("RGB")
        prev.thumbnail((500, 600), Image.LANCZOS)
        pp = os.path.join(a.out, f"{rid}-{way}-preview.png")
        prev.save(pp)
        print(f"wrote {pp}")

    proof, coverage = silhouette(art)
    proof.thumbnail((500, 600), Image.LANCZOS)
    sp = os.path.join(a.out, f"{rid}-silhouette.png")
    proof.save(sp)
    print(f"wrote {sp}")

    print(f"\nink coverage {coverage:.1%}")
    if coverage < 0.08:
        print("⚠ under 8% — this will disappear on a shirt from across a room. "
              "Scale the subject up or add weight.", file=sys.stderr)
    elif coverage > 0.55:
        print("⚠ over 55% — a slab this solid costs ink, feels heavy and cracks "
              "at the fold. Open it up.", file=sys.stderr)

    if a.draft:
        print(f"\nDRAFT at 1/{DRAFT_DIVISOR} scale — not for upload.")

    print("\nLook at the previews and the silhouette before you print. The grey "
          "shows what is transparent; the silhouette is the arm's-length test.")

    if a.report:
        print("\n--- internal ---")
        for n in notes:
            print(f"  {n}")
        srcs = [l.get("provenance", {}).get("credit") or l["source"]
                for l in recipe["layers"]]
        print("\n--- listing copy: only what was actually applied ---")
        print("Suggested design paragraph closer:")
        print(f"  Built from {len(srcs)} public-domain plates, cut out, unified to "
              f"one ink and composed for the print area. Made after you order it.")
        print("\nVerify every clause against the file you upload.")


if __name__ == "__main__":
    main()
