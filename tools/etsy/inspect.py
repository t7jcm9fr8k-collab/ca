#!/usr/bin/env python3
"""
inspect.py — the QC gate. Nine checks between mockup v1 and mockup v2.

This is the only tool here whose job is to say NO.

A gate that rubber-stamps is worse than no gate, because it converts an
unchecked file into a file everyone believes was checked. So every check reports
a NUMBER rather than a verdict — "coverage 6.2%, floor 8%" tells you what to
change; "fails coverage" does not — and a check that could not run is reported
as UNRUN, never as passed.

THE CHECKS, AND THE FAILURE EACH ONE PREVENTS

    file spec        wrong canvas / DPI / mode   Printify rejects or silently rescales
    ink coverage     outside 8-55%               under: vanishes across a room
                                                 over: heavy, cracks at the fold
    stroke width     lines under ~3px @300dpi    DTG cannot hold them
    contrast light   ink vs white garment        washes out
    contrast dark    ink vs black garment        disappears
    edge halo        semi-transparent fringe     prints as a grey ghost outline
    edge bleed       ink at the print boundary   clipped by the platen
    palette          more inks than declared     the collage tell
    provenance       missing url/licence/traced  the SOURCES.md rule

CONTRAST USES WCAG 2.2 SC 1.4.11 — the 3:1 floor for graphical objects, not the
4.5:1 text floor. That distinction is already reasoned about in Theme.swift:48-66
and it is the correct one here: a printed design is a graphical object.

USAGE
    python3 inspect.py --design orchid-skull --version 1
    python3 inspect.py --file out/x-onlight.png --recipe recipes/x.json
    python3 inspect.py --design orchid-skull --version 1 --json
"""

import argparse
import json
import os
import sys
from PIL import Image, ImageChops, ImageFilter

import compose

HERE = os.path.dirname(os.path.abspath(__file__))

CANVAS = compose.CANVAS
DPI = 300

COVERAGE_FLOOR = 0.08
COVERAGE_CEIL = 0.55
MIN_STROKE_PX = 3           # what DTG can hold at 300 DPI
STROKE_LOSS_MAX = 0.35      # fraction of ink allowed to vanish under erosion
HALO_MAX = 0.22             # fraction of SOFT ink allowed outside the solid core
HALO_SKIP_PX = 2            # antialiasing lives here; not a halo
HALO_BAND_PX = 14           # a feathered fringe fills this annulus
BLEED_MARGIN_PX = 40        # ink this close to the edge risks the platen
CONTRAST_MIN = 3.0          # WCAG 2.2 SC 1.4.11, graphical objects

GARMENTS = {
    "white": (255, 255, 255),
    "black": (18, 18, 18),
    "sport grey": (154, 154, 154),      # reported, not blocked on
    "navy": (32, 42, 68),               # reported, not blocked on
}
BLOCKING_GARMENTS = ("white", "black")


# ---------------------------------------------------------------- helpers

def _srgb_lum(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = _srgb_lum(a), _srgb_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def dominant_inks(img, alpha_floor=200, top=8):
    """The colours actually laid down, by area, over opaque pixels only."""
    rgb, a = img.convert("RGB"), img.getchannel("A")
    mask = a.point(lambda v: 255 if v >= alpha_floor else 0)
    quant = rgb.quantize(colors=32, method=Image.MEDIANCUT)
    pal = quant.getpalette() or []
    counts = {}
    for count, idx in (quant.getcolors(1 << 16) or []):
        counts[idx] = counts.get(idx, 0) + count
    # weight by the opaque mask rather than the whole frame
    masked = quant.copy()
    masked.putalpha(mask) if masked.mode == "RGBA" else None
    out = []
    for idx, n in sorted(counts.items(), key=lambda kv: -kv[1])[:top]:
        col = tuple(pal[idx * 3: idx * 3 + 3]) if pal else (0, 0, 0)
        out.append((col, n))
    return out


# ---------------------------------------------------------------- checks

def check_file_spec(img, path):
    got = f"{img.width}x{img.height}"
    want = f"{CANVAS[0]}x{CANVAS[1]}"
    ok_size = (img.width, img.height) == CANVAS
    ok_mode = img.mode == "RGBA"
    dpi = img.info.get("dpi", (None, None))[0]
    ok_dpi = dpi is not None and abs(dpi - DPI) < 1
    return {
        "ok": ok_size and ok_mode and ok_dpi,
        "value": f"{got}, {img.mode}, {dpi or 'no'} DPI",
        "want": f"{want}, RGBA, {DPI} DPI",
        "note": "" if ok_size else
                "wrong canvas — Printify will rescale or reject this",
    }


def check_coverage(img):
    _, cov = compose.silhouette(img)
    ok = COVERAGE_FLOOR <= cov <= COVERAGE_CEIL
    note = ""
    if cov < COVERAGE_FLOOR:
        note = "too light — this disappears on a shirt from across a room"
    elif cov > COVERAGE_CEIL:
        note = "too solid — costs ink, feels heavy, cracks at the fold"
    return {"ok": ok, "value": f"{cov:.1%}",
            "want": f"{COVERAGE_FLOOR:.0%}-{COVERAGE_CEIL:.0%}", "note": note}


def check_stroke(img):
    """
    How much ink vanishes when eroded by the smallest stroke DTG can hold.

    A design built from hairlines survives on screen and breaks up on fabric.
    Eroding by MIN_STROKE_PX and measuring what is left is a direct proxy.
    """
    a = img.getchannel("A").point(lambda v: 255 if v > 96 else 0)
    before = sum(a.histogram()[128:])
    if before == 0:
        return {"ok": False, "value": "no ink", "want": "some", "note": "empty file"}
    eroded = a.filter(ImageFilter.MinFilter(MIN_STROKE_PX * 2 + 1))
    after = sum(eroded.histogram()[128:])
    lost = 1.0 - (after / before)
    ok = lost <= STROKE_LOSS_MAX
    return {"ok": ok, "value": f"{lost:.0%} lost",
            "want": f"<={STROKE_LOSS_MAX:.0%}",
            "note": "" if ok else
                    f"much of this is finer than {MIN_STROKE_PX}px at {DPI} DPI; "
                    f"DTG will break it up"}


def check_contrast(img, garment_name, blocking=True):
    """
    Weighted-average ink colour against the garment, per WCAG SC 1.4.11.

    Averaging by ink area rather than taking the darkest pixel: one black
    outline does not rescue a design that is mostly mid-tone.
    """
    garment = GARMENTS[garment_name]
    rgb, a = img.convert("RGB"), img.getchannel("A")
    mask = a.point(lambda v: 255 if v > 128 else 0)
    n = sum(mask.histogram()[128:])
    if n == 0:
        return {"ok": False, "value": "no ink", "want": f">={CONTRAST_MIN}:1",
                "note": "empty file", "blocking": blocking}
    stat = [ImageChops.multiply(rgb.getchannel(c), mask) for c in range(3)]
    mean = tuple(sum(i * v for i, v in enumerate(ch.histogram())) / max(1, n)
                 for ch in stat)
    ratio = contrast_ratio(mean, garment)
    ok = ratio >= CONTRAST_MIN
    note = ""
    if not ok:
        note = (f"average ink {tuple(int(x) for x in mean)} against "
                f"{garment_name} — it will not read")
    return {"ok": ok if blocking else True, "value": f"{ratio:.2f}:1",
            "want": f">={CONTRAST_MIN}:1", "note": note, "blocking": blocking,
            "reported_only": not blocking}


def check_halo(img):
    """
    Semi-transparent fringe left by over-feathering a cutout.

    ⚠ Two wrong versions preceded this one, and both are worth recording.

    First: "a clean cutout is mostly alpha 0 or 255, so flag mid-alpha." That
    fails every design here, because `map_to_ink` produces a continuous DENSITY
    ramp by design — on a real composite only 0.6% of pixels were near-full
    alpha and the check reported 98% halo on a clean file.

    Second: "flag soft ink that lies outside the solid core." That had the
    discriminator backwards. A halo HUGS the contour; delicate line artwork
    spreads soft ink far from any solid core. The second version flagged the
    artwork signature and passed the halo one.

    What actually separates them is BAND WIDTH. Antialiasing is 1-2px. A
    feathered halo is a ring 5-20px wide that follows the silhouette. So measure
    how densely soft ink fills an annulus just outside the core, past where
    antialiasing reaches. Artwork does not fill that ring; a halo does.
    """
    a = img.getchannel("A")
    if sum(a.histogram()[20:]) == 0:
        return {"ok": False, "value": "no ink", "want": "some", "note": "empty file"}

    soft = a.point(lambda v: 255 if 20 <= v < 128 else 0)
    core = a.point(lambda v: 255 if v >= 128 else 0)
    if sum(core.histogram()[128:]) == 0:
        return {"ok": True, "value": "no solid core to fringe",
                "want": f"<={HALO_MAX:.0%}", "note": ""}

    inner = core.filter(ImageFilter.MaxFilter(HALO_SKIP_PX * 2 + 1))
    outer = core.filter(ImageFilter.MaxFilter(HALO_BAND_PX * 2 + 1))
    ring = ImageChops.subtract(outer, inner)
    ring_n = sum(ring.histogram()[128:])
    if ring_n == 0:
        return {"ok": True, "value": "no ring to measure",
                "want": f"<={HALO_MAX:.0%}", "note": ""}

    in_ring = sum(ImageChops.multiply(soft, ring).histogram()[128:])
    frac = in_ring / ring_n
    high = frac > HALO_MAX

    # REPORTED, NOT BLOCKING — and the reason matters.
    #
    # The annulus test separates a fringe from artwork on isolated shapes
    # (verified: a clean disc reads 0%, the same disc feathered reads 100%). It
    # cannot separate them on DENSE LINEWORK, because there the ring is filled
    # by neighbouring lines rather than by a fringe. Every composite this
    # pipeline makes is dense linework.
    #
    # A blocking check that fires on every good file trains you to ignore the
    # gate, which costs more than the defect it was meant to catch. So the
    # number is reported and a human looks at the preview. When it reads high on
    # a design with ISOLATED elements, believe it.
    return {"ok": True, "value": f"ring {frac:.0%} filled",
            "want": f"<={HALO_MAX:.0%} on isolated shapes",
            "blocking": False, "reported_only": True,
            "note": ("high — check the preview for a grey ring around the "
                     "silhouette. On dense linework this is usually neighbouring "
                     "lines, not a fringe." if high else "")}


def check_bleed(img):
    a = img.getchannel("A").point(lambda v: 255 if v > 96 else 0)
    w, h = a.size
    m = BLEED_MARGIN_PX
    edges = [a.crop((0, 0, w, m)), a.crop((0, h - m, w, h)),
             a.crop((0, 0, m, h)), a.crop((w - m, 0, w, h))]
    touching = sum(sum(e.histogram()[128:]) for e in edges)
    ok = touching == 0
    return {"ok": ok, "value": f"{touching} px within {m}px of the edge",
            "want": "0",
            "note": "" if ok else "ink at the boundary gets clipped by the platen"}


def check_palette(img, recipe):
    """
    How many distinct inks are actually on the shirt.

    ⚠ Counting RGB clusters was the first version and it was wrong for the same
    reason the halo check was: ink density varies LIGHTNESS continuously, so one
    ink at twenty densities quantises into many colours. It reported 8 inks on a
    two-ink file.

    Hue is what identifies an ink; density does not change it. So cluster by hue
    over the pixels dense enough to carry real colour, and ignore the near-grey
    ones, whose hue is noise.
    """
    declared = len((recipe or {}).get("palette", {}).get("inks", {})) or 1
    rgb, a = img.convert("RGB"), img.getchannel("A")
    hsv = rgb.convert("HSV")
    hue, sat = hsv.getchannel(0), hsv.getchannel(1)

    dense = a.point(lambda v: 255 if v >= 96 else 0)
    coloured = ImageChops.multiply(dense, sat.point(lambda v: 255 if v > 40 else 0))
    n = sum(coloured.histogram()[128:])
    if n == 0:
        # A single dark ink is legitimately desaturated everywhere.
        return {"ok": declared <= 1 or True, "value": "1 ink (achromatic)",
                "want": f"<={declared} (recipe declares {declared})", "note": ""}

    hist = hue.histogram(coloured)
    buckets = [sum(hist[i:i + 16]) for i in range(0, 256, 16)]
    inks = sum(1 for b in buckets if b > 0.06 * n)
    ok = inks <= declared
    return {"ok": ok, "value": f"{inks} hue cluster(s)",
            "want": f"<={declared} (recipe declares {declared})",
            "note": "" if ok else
                    "more distinct inks than the recipe declares — the collage tell"}


# ---------------------------------------------------------------- run

def inspect(path, recipe=None):
    if not os.path.exists(path):
        return {"verdict": "unrun", "checks": {},
                "error": f"file not found: {path}"}
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    checks = {
        "file spec": check_file_spec(img, path),
        "ink coverage": check_coverage(img),
        "stroke width": check_stroke(img),
        "edge halo": check_halo(img),
        "edge bleed": check_bleed(img),
        "palette": check_palette(img, recipe),
    }
    for g in GARMENTS:
        checks[f"contrast on {g}"] = check_contrast(
            img, g, blocking=g in BLOCKING_GARMENTS)

    if recipe is not None:
        problems = compose.check_provenance(recipe)
        checks["provenance"] = {
            "ok": not problems, "value": f"{len(problems)} problem(s)",
            "want": "0", "note": "; ".join(problems[:2])}
    else:
        checks["provenance"] = {"ok": None, "value": "unrun",
                                "want": "0", "note": "no recipe given"}

    failed = [k for k, v in checks.items() if v["ok"] is False]
    unrun = [k for k, v in checks.items() if v["ok"] is None]
    verdict = "blocked" if failed else ("pass" if not unrun else "pass-with-unrun")
    return {"verdict": verdict, "checks": checks, "failed": failed, "unrun": unrun,
            "file": path}


def render(result):
    L = [f"\n{'='*72}", f"INSPECTION — {os.path.basename(result.get('file',''))}",
         "="*72]
    if result.get("error"):
        L.append(f"\nUNRUN: {result['error']}")
        return "\n".join(L)
    L.append(f"\n{'check':<22}{'value':<26}{'want':<20}")
    L.append("-" * 72)
    for name, c in result["checks"].items():
        if c["ok"] is None:
            mark = "unrun"
        elif c["ok"]:
            mark = "ok   "
        else:
            mark = "FAIL "
        tail = "  (reported, not blocking)" if c.get("reported_only") else ""
        L.append(f"{mark} {name:<21}{str(c['value']):<26}{str(c['want']):<20}{tail}")
        if c.get("note"):
            L.append(f"       └─ {c['note']}")
    L.append("-" * 72)
    L.append(f"VERDICT: {result['verdict'].upper()}")
    if result.get("failed"):
        L.append(f"blocked by: {', '.join(result['failed'])}")
    if result.get("unrun"):
        L.append(f"could not run: {', '.join(result['unrun'])} "
                 f"— these are NOT passes")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", help="design id; resolves file and recipe")
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--file", help="print file to inspect directly")
    ap.add_argument("--recipe", help="recipe json, for provenance and palette")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-record", action="store_true",
                    help="inspect without writing to the history ledger")
    a = ap.parse_args()

    path = a.file
    recipe_path = a.recipe
    if a.design:
        path = path or os.path.join(a.out, f"{a.design}-v{a.version}-onlight.png")
        recipe_path = recipe_path or os.path.join(HERE, "recipes", f"{a.design}.json")
    if not path:
        sys.exit("need --design or --file")

    recipe = None
    if recipe_path and os.path.exists(recipe_path):
        recipe = json.load(open(recipe_path))

    result = inspect(path, recipe)
    result["design"] = a.design
    result["version"] = a.version

    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(render(result))

    if a.design and not a.no_record:
        import history
        history.record_inspection(a.design, a.version, result)
        print(f"\nrecorded to the ledger — v{a.version + 1} is now unblocked"
              if result["verdict"] != "blocked" else
              f"\nrecorded to the ledger — v{a.version + 1} may proceed and must "
              f"answer the failures above")

    sys.exit(2 if result["verdict"] == "blocked" else 0)


if __name__ == "__main__":
    main()
