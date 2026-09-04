#!/usr/bin/env python3
"""
printable.py — export a finished composite as wall-art printables.

A digital download is the same design sold a second time at zero marginal
cost: the buyer prints it themselves. The research graded it "weak" on
anonymity because a file travels with whatever metadata was inside it, so this
tool exists to make the file boring — pixels, a size, a resolution, and
nothing else.

WHAT IT WRITES, PER SIZE
    out/printables/<id>-8x10.png     RGB, 300 DPI, art centred on the ground
    out/printables/<id>-8x10.pdf     one page, same pixels, for the print shop
    ... and the same for 11x14, A3 and 16x20

THE THREE RULES
    1. Never stretch. The art is scaled to FIT inside the size minus its
       margin, aspect preserved, and centred. A 15x18 print file goes onto an
       8x10 at 0.44 scale; onto a 16x20 at 1.0. It is never scaled UP — a
       composite that has to be enlarged to fill a sheet will print soft, and
       the fix is a bigger source, not a bigger number.
    2. Nothing but pixels. Every output is built on a fresh canvas from pixel
       data, so no EXIF, XMP, tEXt or PDF info survives from the source. After
       writing, each file is reopened and checked: a PNG may carry only its
       DPI; a PDF is scanned for /Author, /Creator, /Producer, /Title and
       the date stamps. The PDF is written by hand for exactly this reason.
    3. Scrubbed. Every output's bytes are searched for the strings given with
       --forbid (your name, your town, the old team ID — pass them on your
       own machine; they are never written into this repo). A hit deletes the
       file and exits 5. A leak is a stop, not a note.

THE GATE
    A printable is a sale file, so it comes only from a design version that
    has a recorded inspection that was not blocked. `--force` goes around the
    gate and, like every bypass here, needs `--force-reason` (exit 4 without
    one) and is printed in the summary so it is visible.

USAGE
    python3 printable.py --design marigold-calavera --version 2 \\
        --print out/marigold-calavera-onlight.png --forbid "Your Name" --forbid "Your Town"
    python3 printable.py --design x --version 2 --print out/x-onlight.png --sizes 8x10 a3
"""

import argparse
import os
import re
import sys
from PIL import Image

import history

HERE = os.path.dirname(os.path.abspath(__file__))

DPI = 300
MARGIN_IN = 0.5
GROUND = "#FFFFFF"

# Inches. A3 is the one non-US size buyers ask for.
SIZES = {
    "8x10": (8.0, 10.0),
    "11x14": (11.0, 14.0),
    "a3": (11.69, 16.54),
    "16x20": (16.0, 20.0),
}

# PDF info keys that would name a person or a tool. None may appear.
PDF_INFO_KEYS = (b"/Author", b"/Creator", b"/Producer", b"/Title", b"/Subject",
                 b"/Keywords", b"/CreationDate", b"/ModDate", b"/Info")


def parse_hex(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def fit(art, size_in, dpi=DPI, margin_in=MARGIN_IN, ground=GROUND):
    """
    Place `art` (RGBA, transparent ground) on a fresh RGB canvas of `size_in`
    inches at `dpi`, scaled to fit inside the margin, centred, never enlarged.

    Returns (image, info) where info carries the numbers a reader would want
    to check: canvas px, art px after scaling, the scale, and the margin px.
    """
    w, h = int(round(size_in[0] * dpi)), int(round(size_in[1] * dpi))
    m = int(round(margin_in * dpi))
    box = art.getbbox()
    if box is None:
        raise ValueError("the print file has no ink")
    trimmed = art.crop(box)
    aw, ah = trimmed.size
    avail_w, avail_h = w - 2 * m, h - 2 * m
    if avail_w <= 0 or avail_h <= 0:
        raise ValueError("margin larger than the sheet")
    scale = min(avail_w / aw, avail_h / ah, 1.0)
    tw, th = max(1, int(round(aw * scale))), max(1, int(round(ah * scale)))
    placed = trimmed.resize((tw, th), Image.LANCZOS) if scale < 1.0 else trimmed
    canvas = Image.new("RGB", (w, h), parse_hex(ground))
    x, y = (w - tw) // 2, (h - th) // 2
    canvas.paste(placed, (x, y), placed)
    info = {"canvas_px": (w, h), "art_px": (tw, th), "scale": round(scale, 4),
            "margin_px": m, "offset": (x, y)}
    return canvas, info


def pdf_bytes(img, dpi=DPI):
    """
    A one-page PDF holding `img` as a Flate-compressed RGB image, written by
    hand so the file carries exactly four objects and no /Info dictionary.
    Pillow's own PDF writer puts the filename into /Title and stamps
    /CreationDate and /ModDate; a file meant to carry nothing but pixels
    should not have a writer that adds things on its own.
    """
    import zlib
    w, h = img.size
    pw, ph = w * 72.0 / dpi, h * 72.0 / dpi
    data = zlib.compress(img.tobytes(), 9)
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw:.2f} {ph:.2f}] "
         f"/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>").encode(),
        (f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} "
         f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
         f"/Length {len(data)} >>\nstream\n").encode() + data + b"\nendstream",
    ]
    content = f"q {pw:.2f} 0 0 {ph:.2f} 0 0 cm /Im0 Do Q".encode()
    objs.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offsets:
        out += f"{o:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n"
            f"%%EOF\n").encode()
    return bytes(out)


def write(img, path_png, path_pdf, dpi=DPI):
    """Write PNG and PDF from a fresh image. No metadata is offered to either."""
    clean = Image.frombytes("RGB", img.size, img.convert("RGB").tobytes())
    clean.save(path_png, "PNG", dpi=(dpi, dpi))
    with open(path_pdf, "wb") as f:
        f.write(pdf_bytes(clean, dpi))


def audit(path, forbid=()):
    """
    Reopen a written file and report what it carries. Returns a list of
    problems; empty means clean. Forbidden strings are matched case-
    insensitively against the raw bytes.
    """
    problems = []
    raw = open(path, "rb").read()
    if path.lower().endswith(".png"):
        im = Image.open(path)
        extra = sorted(k for k in im.info if k != "dpi")
        if extra:
            problems.append(f"png carries metadata: {', '.join(extra)}")
        if im.mode != "RGB":
            problems.append(f"png mode is {im.mode}, not RGB")
    elif path.lower().endswith(".pdf"):
        if not raw.startswith(b"%PDF"):
            problems.append("not a PDF")
        for k in PDF_INFO_KEYS:
            if k in raw:
                problems.append(f"pdf carries {k.decode()}")
    low = raw.lower()
    for s in forbid:
        s = str(s).strip()
        if s and s.lower().encode() in low:
            problems.append(f"forbidden string present: {s!r}")
    return problems


def export(art, design, out_dir, sizes=None, dpi=DPI, margin_in=MARGIN_IN,
           ground=GROUND, forbid=()):
    """
    Write every size. Returns a list of per-size records. Raises RuntimeError
    on any audit problem AFTER deleting the offending files — nothing that
    failed the audit is left on disk to be uploaded by mistake.
    """
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for name in (sizes or list(SIZES)):
        if name not in SIZES:
            raise ValueError(f"unknown size {name!r}; sizes are {', '.join(SIZES)}")
        img, info = fit(art, SIZES[name], dpi, margin_in, ground)
        png = os.path.join(out_dir, f"{design}-{name}.png")
        pdf = os.path.join(out_dir, f"{design}-{name}.pdf")
        write(img, png, pdf, dpi)
        problems = audit(png, forbid) + audit(pdf, forbid)
        if problems:
            for p in (png, pdf):
                if os.path.exists(p):
                    os.remove(p)
            raise RuntimeError(f"{name}: " + "; ".join(problems))
        out.append({"size": name, "inches": SIZES[name], "png": png, "pdf": pdf,
                    "bytes": os.path.getsize(png) + os.path.getsize(pdf), **info})
    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", required=True)
    ap.add_argument("--version", type=int, required=True,
                    help="the mockup version whose inspection clears this export")
    ap.add_argument("--print", dest="print_file", required=True,
                    help="the -onlight.png print file (transparent ground)")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "printables"))
    ap.add_argument("--sizes", nargs="+", default=list(SIZES),
                    help=f"any of {', '.join(SIZES)}")
    ap.add_argument("--margin", type=float, default=MARGIN_IN, help="inches")
    ap.add_argument("--ground", default=GROUND, help="hex, the paper colour")
    ap.add_argument("--forbid", action="append", default=[],
                    help="a string that must not appear in any output; repeatable")
    ap.add_argument("--force", action="store_true",
                    help="export without a recorded, unblocked inspection of this "
                         "version. Needs --force-reason; printed in the summary.")
    ap.add_argument("--force-reason", default="")
    a = ap.parse_args()

    if not os.path.exists(a.print_file):
        sys.exit(f"no print file at {a.print_file}")

    insp = history.inspection_for(a.design, a.version)
    cleared = insp is not None and insp.get("verdict") != "blocked"
    if not cleared and not a.force:
        why = ("no inspection recorded" if insp is None
               else f"inspection verdict is {insp.get('verdict')}")
        print(f"REFUSED — {a.design} v{a.version}: {why}.", file=sys.stderr)
        print("A printable is a sale file. Run qc.py on this version first, or "
              "--force with --force-reason to go around the gate visibly.",
              file=sys.stderr)
        sys.exit(3)
    if a.force and not cleared and not a.force_reason.strip():
        print("--force needs --force-reason: a bypass with no stated reason cannot "
              "be read later.", file=sys.stderr)
        sys.exit(4)

    art = Image.open(a.print_file).convert("RGBA")
    try:
        recs = export(art, a.design, a.out, a.sizes, DPI, a.margin, a.ground, a.forbid)
    except RuntimeError as e:
        print(f"SCRUB FAILED — {e}", file=sys.stderr)
        print("The offending files were deleted. Nothing from this run is safe to "
              "upload.", file=sys.stderr)
        sys.exit(5)
    except ValueError as e:
        sys.exit(str(e))

    if a.force and not cleared:
        print(f"GATE BYPASSED — reason: {a.force_reason.strip()}")
    print(f"{a.design}: {len(recs)} size(s), {len(a.forbid)} forbidden string(s) "
          f"checked, source {art.size[0]}x{art.size[1]}")
    for r in recs:
        print(f"  {r['size']:<6} {r['inches'][0]:>5}x{r['inches'][1]:<5} in  "
              f"canvas {r['canvas_px'][0]}x{r['canvas_px'][1]}  art "
              f"{r['art_px'][0]}x{r['art_px'][1]}  scale {r['scale']:.2f}  "
              f"{r['bytes'] / 1e6:.1f} MB")
    print(f"  written to {a.out}")


if __name__ == "__main__":
    main()
