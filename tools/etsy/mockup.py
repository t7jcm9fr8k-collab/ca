#!/usr/bin/env python3
"""
mockup.py — put a print file on a garment, so it can be judged as a product.

THE GATE, WHICH IS THE POINT OF THIS FILE
    `--version 2` refuses to run unless an inspection of version 1 is recorded
    in the ledger. The second mockup exists to answer findings from the first;
    building it without them makes it a second guess rather than a revision.

    If you find yourself wanting to skip the gate, that is the gate working.

WHY THE MOCKUP IS BUILT RATHER THAN PASTED
    Physical scale is computed, not eyeballed: a 15in print across a 22in chest
    is 68% of the garment width, and a design that looks right at the wrong
    scale is the most common self-inflicted POD error. Fabric noise and a soft
    vertical shade are applied so it reads as cloth — a flat pasted rectangle
    flatters a design that would actually fail.

    A mockup is evidence, not marketing. Nothing here retouches a design to make
    it look better than the file is.

WHAT IT WRITES, PER VERSION
    <id>-v<N>-onlight.png    the print file itself, for inspection
    <id>-v<N>-white.png      on a white garment
    <id>-v<N>-black.png      on a black garment
    <id>-v<N>-detail.png     1:1 crop, where fine linework lives or dies
    <id>-v<N>-sheet.png      contact sheet

USAGE
    python3 mockup.py --design orchid-skull --version 1 --print out/x-onlight.png
    python3 mockup.py --design orchid-skull --version 2 --print out/x2.png \\
                      --change "raised gamma to 0.85" --change "scaled skull to 0.66"
"""

import argparse
import os
import sys
from PIL import Image, ImageDraw, ImageFilter

import history

HERE = os.path.dirname(os.path.abspath(__file__))

# Garment canvas. 1800px across ~22in of flat chest -> ~82 px per inch.
GARMENT = (1800, 2200)
PX_PER_IN = GARMENT[0] / 22.0
PRINT_IN = (15.0, 18.0)                      # Printify front print area
COLLAR_DROP_IN = 3.2                         # top of print below the collar

GARMENT_COLOURS = {
    "white": (247, 246, 243),
    "black": (26, 26, 28),
}


def garment_base(colour):
    """
    A tee silhouette with fabric texture.

    Procedural on purpose — there is no licensed blank photo in this repo, and a
    generated base that is honest about scale beats a borrowed photo that is not
    ours to ship. Swap in a real Printify blank export whenever one exists.
    """
    w, h = GARMENT
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    body_top = int(h * 0.11)
    shoulder = int(w * 0.16)
    d.polygon([(shoulder, body_top), (w - shoulder, body_top),
               (w - int(w * 0.13), h - int(h * 0.04)),
               (int(w * 0.13), h - int(h * 0.04))], fill=colour + (255,))
    # sleeves
    d.polygon([(shoulder, body_top), (int(w * 0.03), int(h * 0.30)),
               (int(w * 0.10), int(h * 0.40)), (shoulder, int(h * 0.26))],
              fill=colour + (255,))
    d.polygon([(w - shoulder, body_top), (w - int(w * 0.03), int(h * 0.30)),
               (w - int(w * 0.10), int(h * 0.40)), (w - shoulder, int(h * 0.26))],
              fill=colour + (255,))
    # collar
    d.ellipse([int(w * 0.40), body_top - int(h * 0.030),
               int(w * 0.60), body_top + int(h * 0.036)],
              fill=(0, 0, 0, 0))

    # Fabric: fine noise plus a soft vertical shade, so it is not a flat slab.
    noise = Image.effect_noise((w, h), 9).convert("L").filter(
        ImageFilter.GaussianBlur(0.6))
    shade = Image.linear_gradient("L").resize((w, h)).point(
        lambda v: 128 + (v - 128) // 7)
    tex = Image.blend(noise, shade, 0.55).point(lambda v: 118 + v // 5)

    rgb = img.convert("RGB")
    rgb = Image.blend(rgb, Image.composite(rgb, rgb, tex), 0.0)
    lit = rgb.point(lambda v: v)
    out = Image.merge("RGBA", (*lit.split(), img.getchannel("A")))

    body = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    body.paste(out, (0, 0), img.getchannel("A"))
    grain = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grain.putalpha(tex.point(lambda v: max(0, min(26, abs(v - 128)))))
    body = Image.alpha_composite(body, grain)
    body.putalpha(img.getchannel("A"))
    return body


def place_print(garment, print_img):
    """Composite at true physical scale, centred in the print area."""
    pw = int(PRINT_IN[0] * PX_PER_IN)
    ph = int(PRINT_IN[1] * PX_PER_IN)
    art = print_img.copy()
    art.thumbnail((pw, ph), Image.LANCZOS)

    x = (GARMENT[0] - art.width) // 2
    y = int(GARMENT[1] * 0.11 + COLLAR_DROP_IN * PX_PER_IN)

    # Ink sits IN the weave, not on it: a touch of blur and a small alpha
    # reduction is what stops it reading as a sticker.
    art = art.filter(ImageFilter.GaussianBlur(0.4))
    art.putalpha(art.getchannel("A").point(lambda v: int(v * 0.94)))

    out = garment.copy()
    out.paste(art, (x, y), art)
    return out, (x, y, art.width, art.height)


def detail_crop(print_img, size=900):
    """A 1:1 slice of the densest region — where fine linework survives or dies."""
    a = print_img.getchannel("A")
    bbox = a.getbbox() or (0, 0, print_img.width, print_img.height)
    cx = (bbox[0] + bbox[2]) // 2
    cy = (bbox[1] + bbox[3]) // 2
    half = size // 2
    box = (max(0, cx - half), max(0, cy - half),
           min(print_img.width, cx + half), min(print_img.height, cy + half))
    crop = print_img.crop(box)
    bg = Image.new("RGBA", crop.size, (247, 246, 243, 255))
    return Image.alpha_composite(bg, crop)


def contact_sheet(images, labels, cols=2, cell=(620, 760)):
    rows = (len(images) + cols - 1) // cols
    pad, head = 20, 34
    W = cols * cell[0] + pad * (cols + 1)
    H = rows * (cell[1] + head) + pad * (rows + 1)
    sheet = Image.new("RGB", (W, H), (250, 250, 249))
    d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(zip(images, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (cell[0] + pad)
        y = pad + r * (cell[1] + head + pad)
        d.text((x, y + 8), lab, fill=(60, 58, 54))
        t = im.convert("RGB").copy()
        t.thumbnail(cell, Image.LANCZOS)
        sheet.paste(t, (x + (cell[0] - t.width) // 2, y + head))
    return sheet


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", required=True)
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--print", dest="print_file", required=True,
                    help="the 4500x5400 print file")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--change", action="append", default=[],
                    help="what changed since the previous version; repeatable")
    ap.add_argument("--note", default="")
    ap.add_argument("--force", action="store_true",
                    help=argparse.SUPPRESS)     # deliberately undocumented
    a = ap.parse_args()

    # ---- the gate -------------------------------------------------------
    if a.version > 1 and not a.force:
        prev = history.inspection_for(a.design, a.version - 1)
        if prev is None:
            print(f"REFUSING to build v{a.version}.\n", file=sys.stderr)
            print(f"  No inspection of v{a.version - 1} is recorded for "
                  f"'{a.design}'.", file=sys.stderr)
            print(f"  A second mockup exists to answer findings from the first. "
                  f"Without\n  them it is a second guess, not a revision.\n",
                  file=sys.stderr)
            print(f"  Run:  python3 inspect.py --design {a.design} "
                  f"--version {a.version - 1}", file=sys.stderr)
            sys.exit(3)
        if not a.change:
            print(f"REFUSING to build v{a.version}.\n", file=sys.stderr)
            print(f"  v{a.version - 1} was inspected ({prev['verdict']}"
                  + (f", failed: {', '.join(prev['failed'])}" if prev.get("failed") else "")
                  + f") but no --change was given.", file=sys.stderr)
            print(f"  A version with no recorded change cannot be read as a "
                  f"revision later.", file=sys.stderr)
            sys.exit(3)
        print(f"gate: v{a.version - 1} inspected {prev['at']} — "
              f"{prev['verdict']}"
              + (f", failed {', '.join(prev['failed'])}" if prev.get("failed") else ""))

    if not os.path.exists(a.print_file):
        sys.exit(f"print file not found: {a.print_file}")

    art = Image.open(a.print_file).convert("RGBA")
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.join(a.out, f"{a.design}-v{a.version}")
    files = {}

    # the print file itself, so inspect.py has a stable path per version
    p = f"{stem}-onlight.png"
    art.save(p, "PNG", dpi=(300, 300))
    files["print"] = p
    files["onlight"] = p

    shots, labels = [], []
    for cname, col in GARMENT_COLOURS.items():
        base = garment_base(col)
        shot, box = place_print(base, art)
        flat = Image.alpha_composite(
            Image.new("RGBA", shot.size, (238, 237, 234, 255)), shot)
        path = f"{stem}-{cname}.png"
        flat.convert("RGB").save(path)
        files[cname if cname != "white" else "white"] = path
        shots.append(flat)
        labels.append(f"{a.design} v{a.version} - {cname} garment")
        print(f"wrote {path}")
    files["ondark"] = files.get("black")

    det = detail_crop(art)
    dpath = f"{stem}-detail.png"
    det.convert("RGB").save(dpath)
    files["detail"] = dpath
    shots.append(det)
    labels.append("detail, 1:1 print resolution")
    print(f"wrote {dpath}")

    sheet = contact_sheet(shots, labels)
    spath = f"{stem}-sheet.png"
    sheet.save(spath)
    files["sheet"] = spath
    print(f"wrote {spath}")

    history.record_version(a.design, a.version, files, a.change, a.note)
    print(f"\nrecorded v{a.version} to the ledger")
    if a.version == 1:
        print(f"next:  python3 inspect.py --design {a.design} --version 1")
    print(f"       python3 history.py --report")


if __name__ == "__main__":
    main()
