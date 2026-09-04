#!/usr/bin/env python3
"""
test_tools.py — checks for the shirt pipeline. Run: python3 test_tools.py

These exist because the two real defects found while building this pipeline were
both invisible in the code and obvious in the output: render_plate.py left the
paper trapped between tentacles opaque, and compose.py's first ink mapping
turned a colour lithograph into faint pencil. Neither would have been caught by
reading. Tests pin the parts that CAN be checked numerically so the eye is saved
for the parts that cannot.

No test framework — stdlib only, same posture as the tools.
"""

import re
import sys
from PIL import Image, ImageDraw, ImageFilter

import compose
import render_plate

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILURES.append(name)


def _raises(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return True
    except Exception:
        return False
    return False


def gradient(w=64, h=64, lo=0, hi=255):
    """A left-to-right luminance ramp between lo and hi."""
    im = Image.new("RGB", (w, h))
    px = im.load()
    for x in range(w):
        v = lo + int((hi - lo) * x / max(1, w - 1))
        for y in range(h):
            px[x, y] = (v, v, v)
    return im


# ---------------------------------------------------------------- ink mapping

print("map_to_ink")

g = gradient()
out = compose.map_to_ink(g, (26, 26, 26), autolevel=False)
a = out.getchannel("A")
check("dark source becomes opaque ink", a.getpixel((0, 32)) > 250,
      f"got {a.getpixel((0, 32))}")
check("light source becomes transparent", a.getpixel((63, 32)) < 5,
      f"got {a.getpixel((63, 32))}")
check("ink colour is flat, source colour discarded",
      out.convert("RGB").getpixel((0, 32)) == (26, 26, 26))

# The defect this pins: a narrow mid-range source (a colour lithograph) must
# still reach full ink density, not come out as faint pencil.
narrow = gradient(lo=110, hi=160)
flat = compose.map_to_ink(narrow, (0, 0, 0), autolevel=False).getchannel("A")
levelled = compose.map_to_ink(narrow, (0, 0, 0), autolevel=True).getchannel("A")
flat_range = max(flat.getdata()) - min(flat.getdata())
lev_range = max(levelled.getdata()) - min(levelled.getdata())
check("autolevel stretches a narrow-range source", lev_range > flat_range * 2,
      f"flat span {flat_range}, levelled span {lev_range}")
check("autolevel reaches near-full density", max(levelled.getdata()) > 240,
      f"peak {max(levelled.getdata())}")

# Autolevel must measure only the opaque region. A cutout reports its
# transparent background as black in grayscale, which would drag the floor to 0
# and flatten everything if it were counted.
cut = gradient(lo=110, hi=160).convert("RGBA")
alpha = Image.new("L", cut.size, 0)
ImageDraw.Draw(alpha).rectangle([16, 16, 47, 47], fill=255)
cut.putalpha(alpha)
cut_out = compose.map_to_ink(cut, (0, 0, 0), autolevel=True).getchannel("A")
inside = [cut_out.getpixel((x, 32)) for x in range(16, 48)]
check("autolevel ignores the transparent region",
      max(inside) - min(inside) > 100, f"span inside cutout {max(inside)-min(inside)}")
check("cutout stays cut out", cut_out.getpixel((2, 2)) == 0)

check("gamma<1 thickens ink",
      sum(compose.map_to_ink(g, (0, 0, 0), gamma=0.5, autolevel=False)
          .getchannel("A").getdata())
      > sum(compose.map_to_ink(g, (0, 0, 0), gamma=2.0, autolevel=False)
            .getchannel("A").getdata()))

# ---------------------------------------------------------------- provenance

print("\nprovenance gate")

base = {"layers": [{"source": "x.png", "provenance": {
    "url": "https://example.org/f", "licence": "public domain", "traced": "2026-09-01"}}]}
check("clean recipe passes", compose.check_provenance(base) == [])

for field in ("url", "licence", "traced"):
    bad = {"layers": [{"source": "x.png", "provenance": dict(base["layers"][0]["provenance"])}]}
    bad["layers"][0]["provenance"][field] = ""
    check(f"missing {field} is caught", len(compose.check_provenance(bad)) == 1)

for lic, why in [("CC-BY-SA 4.0", "share-alike"),
                 ("CC BY-NC 2.0", "noncommercial"),
                 ("probably fine", "unrecognised")]:
    bad = {"layers": [{"source": "x.png", "provenance": dict(base["layers"][0]["provenance"])}]}
    bad["layers"][0]["provenance"]["licence"] = lic
    check(f"{why} licence is refused ({lic})", len(compose.check_provenance(bad)) == 1)

for lic in ("Public Domain", "CC0 1.0", "no known copyright restrictions"):
    ok = {"layers": [{"source": "x.png", "provenance": dict(base["layers"][0]["provenance"])}]}
    ok["layers"][0]["provenance"]["licence"] = lic
    check(f"safe licence accepted ({lic})", compose.check_provenance(ok) == [])

# ---------------------------------------------------------------- silhouette

print("\nsilhouette")

blank = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
_, cov = compose.silhouette(blank)
check("empty art reports zero coverage", cov == 0.0, f"got {cov}")

solid = Image.new("RGBA", (100, 100), (0, 0, 0, 255))
_, cov = compose.silhouette(solid)
check("solid art reports full coverage", cov > 0.99, f"got {cov}")

half = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
ImageDraw.Draw(half).rectangle([0, 0, 49, 99], fill=(0, 0, 0, 255))
_, cov = compose.silhouette(half)
check("half-covered art reports ~50%", 0.45 < cov < 0.55, f"got {cov}")

# ---------------------------------------------------------------- background

print("\nlift_background")

# A dark subject on a light ground, with an enclosed light gap inside it — the
# case that broke the first version: the gap between a jellyfish's tentacles.
plate = Image.new("RGB", (120, 120), (242, 238, 228))
d = ImageDraw.Draw(plate)
d.ellipse([20, 20, 99, 99], fill=(40, 40, 40))
d.ellipse([45, 45, 74, 74], fill=(242, 238, 228))     # enclosed paper

lifted, cleared = render_plate.lift_background(plate, key_enclosed=False, feather=0)
check("border fill clears the outer ground", lifted.getchannel("A").getpixel((2, 2)) == 0)
check("border fill leaves the enclosed gap opaque",
      lifted.getchannel("A").getpixel((60, 60)) > 200,
      f"got {lifted.getchannel('A').getpixel((60, 60))}")

lifted2, cleared2 = render_plate.lift_background(plate, key_enclosed=True, feather=0)
check("second pass clears the enclosed gap",
      lifted2.getchannel("A").getpixel((60, 60)) == 0,
      f"got {lifted2.getchannel('A').getpixel((60, 60))}")
check("second pass keeps the subject", lifted2.getchannel("A").getpixel((30, 60)) > 200)
check("second pass clears strictly more", cleared2 > cleared,
      f"{cleared:.3f} -> {cleared2:.3f}")

# ---------------------------------------------------------------- listing

print("\nlisting — margin")

import listing

# Every figure below is read off CorpalCaptain_Margin_Calculator.xlsx. If one of
# these breaks, the calculator and the code have diverged and the code is wrong.
for retail, fees, keep in [(22.99, 3.0853, 10.1147),
                           (23.99, 3.1803, 11.0197),
                           (24.99, 3.2753, 11.9247)]:
    m = listing.margin(retail)
    check(f"margin at ${retail} matches the calculator",
          abs(m["fees"] - fees) < 0.001 and abs(m["keep"] - keep) < 0.001,
          f"fees {m['fees']:.4f} keep {m['keep']:.4f}")

check("break-even matches the calculator",
      abs(listing.break_even() - 11.8135) < 0.001, f"got {listing.break_even():.4f}")
check("fees are charged on retail PLUS shipping",
      abs(listing.margin(23.99)["buyer_pays"] - 28.74) < 0.001)
check("offsite ads cut the take",
      listing.margin(23.99, offsite_ads=True)["keep"] < listing.margin(23.99)["keep"])
check("break-even price keeps roughly nothing",
      abs(listing.margin(listing.break_even())["keep"]) < 0.01)

print("\nlisting — validators")

check("over-length title is an error",
      any(l == "error" for l, _ in listing.check_title("x" * 141, "x")))
check("141 is over, 140 is not",
      not any(l == "error" for l, _ in listing.check_title("x" * 140, "x")))
check("phrase past char 40 warns",
      any("Move it earlier" in m for _, m in
          listing.check_title("a" * 50 + " Kraken", "Kraken")))
check("phrase missing from title is an error",
      any(l == "error" for l, _ in listing.check_title("nothing here", "Kraken")))

check("21-char tag is an error",
      any(l == "error" for l, _ in listing.check_tags(["a" * 21])))
check("20-char tag is allowed",
      not any("cap is 20" in m for _, m in listing.check_tags(["ab cd " + "e" * 14])))
check("near-twin tags are caught",
      any("near-twins" in m for _, m in listing.check_tags(["moth tee", "moth tees"])))
check("single-word tag warns",
      any("one word" in m for _, m in listing.check_tags(["tee"])))

check("banned word is caught",
      any("tapestry" in m for _, m in listing.check_words("a tapestry of", "x")))
check("off-register word warns",
      any(l == "warn" for l, m in listing.check_words("great quality", "x")))
check("clean copy passes", listing.check_words("A jellyfish drawn in 1904.", "x") == [])

check("_head strips the product word",
      listing._head("dark academia tee") == listing._head("dark academia shirt"))
check("_head keeps different subjects apart",
      listing._head("moth tee") != listing._head("skull tee"))

seven = [f"subject{i} tee" for i in range(7)]
cat_ = {"designs": [{"id": "other", "tags": seven}]}
check("identical tag sets are flagged as cannibalising",
      any("compete" in m for _, m in
          listing.check_cannibalisation("mine", listing.build_tags(seven), cat_)))
check("universal tags alone do not cannibalise",
      listing.check_cannibalisation(
          "mine", listing.UNIVERSAL_TAGS,
          {"designs": [{"id": "o", "tags": listing.UNIVERSAL_TAGS}]}) == [])

print("\nlisting — the real catalogue")

import json as _json
cat = _json.load(open("catalogue.json"))
check("catalogue has 10 designs", len(cat["designs"]) == 10, str(len(cat["designs"])))
errs = 0
for d in cat["designs"]:
    errs += len([i for i in listing.report(d, cat, quiet=True) if i[0] == "error"])
check("every catalogue listing is error-free", errs == 0, f"{errs} errors")
check("build_tags reaches exactly 13",
      all(len(listing.build_tags(d["tags"])) == 13 for d in cat["designs"]))
check("the two live listings are present",
      {"jellyfish-blue", "jellyfish-gold"} <= {d["id"] for d in cat["designs"]})

# ---------------------------------------------------------------- calendar

print("\ncalendar")

import datetime as _dt
import schedule as shirtcal

check("school wall is blacked out",
      shirtcal.in_blackout(_dt.date(2026, 9, 20)))
check("the day before the wall is usable",
      not shirtcal.in_blackout(_dt.date(2026, 9, 12)))
check("the day after the wall is usable",
      not shirtcal.in_blackout(_dt.date(2026, 9, 30)))

rel = shirtcal.release_schedule(cat["designs"], _dt.date(2026, 9, 5))
dates = [d for d, _ in rel]
check("every unreleased design gets a slot", len(rel) == 8, str(len(rel)))
check("no two releases share a date", len(set(dates)) == len(dates))
check("no release lands in the school wall",
      not any(shirtcal.in_blackout(d) for d in dates if d))
check("every release is on or before the cutoff",
      all(d <= shirtcal.RELEASE_CUTOFF for d in dates if d))
check("seasonal designs are released first",
      {r[1]["id"] for r in rel[:3]} >=
      {"marigold-calavera"}, str([r[1]["id"] for r in rel[:3]]))

# A release date for a design with no plates is a date nothing can happen on:
# compose.py refuses to render it. So the calendar puts renderable designs
# first, whatever their id or season, and says plainly which ones are blocked.
# Today every recipe is blocked, and by id the calendar read "Doré first" when
# the two designs whose plates arrive this weekend are Marigold and Orchid.
import json as _json
import os as _os
import shutil as _shutil
import tempfile as _tempfile
_cal_sand = _tempfile.mkdtemp()
_rd, _sd = _os.path.join(_cal_sand, "recipes"), _os.path.join(_cal_sand, "sources")
_os.makedirs(_rd)
_os.makedirs(_sd)
_prov = {"url": "https://example.org/file", "licence": "public domain",
         "traced": "2026-09-05", "credit": "Example Library"}


def _recipe(did, srcs, prov):
    _json.dump({"id": did, "layers": [{"source": x, "provenance": dict(prov)}
                                      for x in srcs]},
               open(_os.path.join(_rd, f"{did}.json"), "w"))


_recipe("kraken-chart", ["kraken.jpg"], _prov)                 # plate in, provenance filled
_recipe("marigold-calavera", ["posada.jpg"], _prov)            # provenance filled, plate MISSING
_recipe("dore-descent", ["dore.jpg"], {k: "" for k in _prov})  # plate in, provenance blank
open(_os.path.join(_sd, "kraken.jpg"), "wb").write(b"x")
open(_os.path.join(_sd, "dore.jpg"), "wb").write(b"x")
_ready = shirtcal.renderable(cat["designs"], _rd, _sd)
check("a design with its plate on disk and provenance filled is renderable",
      _ready == {"kraken-chart"}, str(_ready))
check("a filled recipe whose plate is not on disk is not renderable",
      "marigold-calavera" not in _ready)
check("a plate on disk with blank provenance is not renderable",
      "dore-descent" not in _ready)
check("a design with no recipe at all is not renderable",
      "orchid-skull" not in _ready)
_rel2 = shirtcal.release_schedule(cat["designs"], _dt.date(2026, 9, 5), ready=_ready)
check("the renderable design releases first, ahead of the seasonals",
      _rel2[0][1]["id"] == "kraken-chart", str([r[1]["id"] for r in _rel2[:3]]))
check("seasonal-then-id order still holds among the blocked designs",
      [r[1]["id"] for r in _rel2[1:4]] ==
      ["dore-descent", "fungi-codex", "marigold-calavera"],
      str([r[1]["id"] for r in _rel2[1:4]]))
check("with no readiness given the old order is unchanged",
      [r[1]["id"] for r in rel] ==
      [r[1]["id"] for r in shirtcal.release_schedule(cat["designs"], _dt.date(2026, 9, 5))])
_md2 = shirtcal.to_markdown(_rel2, [], "America/New_York", ready=_ready)
check("the calendar marks every blocked design", _md2.count("BLOCKED") == 7,
      str(_md2.count("BLOCKED")))
check("the renderable design is not marked blocked",
      "| Kraken Chart | spread for the ranking boost |" in _md2)
check("the calendar says how many cannot be rendered yet",
      "7 of 8 cannot be rendered yet" in _md2)
# And a blocked design's provisional date must not put it into Pinterest's
# rotation — main() passes only the renderable releases to posting_schedule.
_live_or_ready = {d["id"] for d in cat["designs"] if d.get("status") == "live"} | _ready
_slots2 = shirtcal.posting_schedule(cat["designs"], _dt.date(2026, 9, 5), _dt.date(2026, 11, 30),
                                    [(d, x) for d, x in _rel2 if x["id"] in _ready])
check("Pinterest never carries a blocked design",
      all(x["design"]["id"] in _live_or_ready for x in _slots2 if x["platform"] == "Pinterest"),
      str({x["design"]["id"] for x in _slots2 if x["platform"] == "Pinterest"} - _live_or_ready))
check("the renderable design does reach Pinterest once released",
      any(x["design"]["id"] == "kraken-chart" for x in _slots2 if x["platform"] == "Pinterest"))
_shutil.rmtree(_cal_sand)

slots = shirtcal.posting_schedule(cat["designs"], _dt.date(2026, 9, 5),
                                  _dt.date(2026, 11, 30))
days = [s["date"] for s in slots]
check("one posting slot per day", len(set(days)) == len(days))
check("no posting slot in the school wall",
      not any(shirtcal.in_blackout(d) for d in days))
check("both platforms are used",
      {s["platform"] for s in slots} == {"Pinterest", "TikTok"})
check("posting times vary across the day",
      len({s["time"] for s in slots}) >= 8,
      str(len({s["time"] for s in slots})))
check("slots span morning and evening",
      any(s["time"][0] < 12 for s in slots) and any(s["time"][0] >= 19 for s in slots))
check("every design appears in the rotation",
      len({s["design"]["id"] for s in slots}) == 10)

# A pin is a conversion asset. One pointing at a design that does not exist yet
# sends the click nowhere, and Pinterest slots keep working for months, so the
# waste compounds.
rel_by_id = {d["id"]: date for date, d in rel if date}
for _d in cat["designs"]:
    if _d.get("status") == "live":
        rel_by_id[_d["id"]] = _dt.date.min
gated = shirtcal.posting_schedule(cat["designs"], _dt.date(2026, 9, 5),
                                  _dt.date(2026, 11, 30), rel)
dead = [x for x in gated if x["platform"] == "Pinterest"
        and rel_by_id.get(x["design"]["id"], _dt.date.max) > x["date"]]
check("no Pinterest slot points at an unreleased design", not dead,
      f"{len(dead)} dead links")
check("TikTok is allowed to tease unreleased designs",
      any(x["platform"] == "TikTok"
          and rel_by_id.get(x["design"]["id"], _dt.date.max) > x["date"]
          for x in gated))
check("every design still reaches Pinterest eventually",
      len({x["design"]["id"] for x in gated if x["platform"] == "Pinterest"}) == 10)

pt, pd_ = shirtcal.pin_copy(cat["designs"][0], "detail crop — the close look")
check("pin title respects the grid cutoff", len(pt) <= shirtcal.PIN_TITLE_MAX, str(len(pt)))
check("pin description respects the cap", len(pd_) <= shirtcal.PIN_DESC_MAX, str(len(pd_)))
check("pin description carries keywords",
      any(t in pd_ for t in cat["designs"][0]["tags"]))
tc, th = shirtcal.tiktok_copy(cat["designs"][0], "layer reveal — sources fading in")
check("tiktok hashtags are hashtags", th.startswith("#") and " #" in th)

ics = shirtcal.to_ics(rel, slots, "America/New_York")
check("ics opens and closes correctly",
      ics.startswith("BEGIN:VCALENDAR") and ics.rstrip().endswith("END:VCALENDAR"))
check("ics has one event per item",
      ics.count("BEGIN:VEVENT") == len([d for d in dates if d]) + len(slots))
check("ics UIDs are unique",
      len(set(re.findall(r"^UID:(.+)$", ics, re.M))) == ics.count("BEGIN:VEVENT"))

# ---------------------------------------------------------------- printables

print("\nprintables")

import printable

_pa = Image.new("RGBA", (300, 360), (0, 0, 0, 0))
ImageDraw.Draw(_pa).rectangle([50, 60, 250, 300], fill=(20, 20, 20, 255))
_fit, _fi = printable.fit(_pa, (8, 10), dpi=30, margin_in=0.5, ground="#FFFFFF")
check("the sheet is the size asked for, at the dpi asked for", _fit.size == (240, 300), str(_fit.size))
check("the art is scaled to fit inside the margin",
      _fi["art_px"][0] <= 240 - 30 and _fi["art_px"][1] <= 300 - 30, str(_fi))
check("the art keeps its aspect ratio",
      abs((_fi["art_px"][0] / _fi["art_px"][1]) - (200 / 240)) < 0.02, str(_fi["art_px"]))
check("the art is centred",
      abs(_fi["offset"][0] * 2 + _fi["art_px"][0] - 240) <= 1
      and abs(_fi["offset"][1] * 2 + _fi["art_px"][1] - 300) <= 1, str(_fi))
check("the margin holds no ink",
      all(_fit.getpixel(p) == (255, 255, 255)
          for p in [(5, 5), (234, 5), (5, 294), (120, 10), (10, 150)]))
_big = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
ImageDraw.Draw(_big).rectangle([10, 10, 50, 50], fill=(0, 0, 0, 255))
_fb, _fbi = printable.fit(_big, (8, 10), dpi=30)
check("small art is never enlarged", _fbi["scale"] == 1.0 and _fbi["art_px"] == (41, 41), str(_fbi))
check("a blank print file is refused", _raises(ValueError, printable.fit, Image.new("RGBA", (10, 10)), (8, 10), 30))

import tempfile as _tf
_pd = _tf.mkdtemp(prefix="printable-")
_recs = printable.export(_pa, "fixture", _pd, sizes=["8x10", "a3"], dpi=30,
                         forbid=["PLANTED-SECRET"])
check("every size asked for is written, as png and pdf",
      [r["size"] for r in _recs] == ["8x10", "a3"]
      and all(_os.path.exists(r["png"]) and _os.path.exists(r["pdf"]) for r in _recs))
_rp = Image.open(_recs[0]["png"])
check("the png carries only its dpi", sorted(_rp.info) == ["dpi"], str(sorted(_rp.info)))
check("the png is plain RGB", _rp.mode == "RGB")
_pdfb = open(_recs[0]["pdf"], "rb").read()
check("the pdf is a pdf", _pdfb.startswith(b"%PDF"))
check("the pdf names no author, creator, producer, title or date",
      not any(k in _pdfb for k in printable.PDF_INFO_KEYS))
import zlib as _zlib
_s0 = _pdfb.index(b"stream\n", _pdfb.index(b"/Subtype /Image")) + 7
_s1 = _pdfb.index(b"\nendstream", _s0)
check("the pdf's image is the png's pixels, byte for byte",
      _zlib.decompress(_pdfb[_s0:_s1]) == _rp.convert("RGB").tobytes())
check("the pdf is one page holding one image at the sheet size",
      _pdfb.count(b"/Type /Page ") == 1 and b"/Subtype /Image" in _pdfb
      and b"/MediaBox [0 0 576.00 720.00]" in _pdfb and _pdfb.rstrip().endswith(b"%%EOF"))
check("a clean file passes the audit", printable.audit(_recs[0]["png"], ["PLANTED-SECRET"]) == [])

# The scrub: plant a string in a written file and make sure the audit sees it
# and the export deletes it. The tEXt chunk is how a name usually travels.
from PIL import PngImagePlugin as _PngInfo
_leak = _os.path.join(_pd, "leak.png")
_pi = _PngInfo.PngInfo()
_pi.add_text("Author", "PLANTED-SECRET")
Image.new("RGB", (8, 8)).save(_leak, "PNG", pnginfo=_pi)
_lp = printable.audit(_leak, ["planted-secret"])
check("planted metadata is reported", any("metadata" in x for x in _lp), str(_lp))
check("a forbidden string is found case-insensitively", any("forbidden" in x for x in _lp), str(_lp))
_real_audit = printable.audit
def _tainted(path, forbid=()):
    return _real_audit(path, forbid) + (["forbidden string present: 'X'"] if path.endswith("11x14.pdf") else [])
printable.audit = _tainted
_raised = _raises(RuntimeError, printable.export, _pa, "tainted", _pd, ["11x14"], 30)
printable.audit = _real_audit
check("an export that fails the scrub raises", _raised)
check("and leaves nothing on disk",
      not _os.path.exists(_os.path.join(_pd, "tainted-11x14.png"))
      and not _os.path.exists(_os.path.join(_pd, "tainted-11x14.pdf")))
check("an unknown size is refused",
      _raises(ValueError, printable.export, _pa, "x", _pd, ["a4"], 30))
_shutil.rmtree(_pd)

# ---------------------------------------------------------------- rival

print("\nrival")

import rival

check("a short response is unreachable, not empty",
      _raises(rival.Unreachable, rival.extract_titles, "<html></html>"))
check("an unparseable full page raises rather than returning zero",
      _raises(rival.Unparseable, rival.extract_titles,
              "<html><body>" + "x" * 5000 + "</body></html>"))
check("matches are counted on the title only",
      rival.count_matches(
          ["Botanical Skull Tee", "Moth Shirt", "botanical skull art"],
          "Botanical Skull") == 2)
check("a genuine zero is still reachable",
      rival.count_matches(["Moth Shirt", "Mug"], "Kraken") == 0)

# ---------------------------------------------------------------- inspect

print("\ninspect — checks")

import qc

def _art(size=(4500, 5400), fill=(26, 26, 26), box=None, dpi=True):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    box = box or [size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4]
    ImageDraw.Draw(im).ellipse(box, fill=fill + (255,))
    return im

good = _art()
check("correct canvas passes file spec",
      qc.check_file_spec(good, "x")["value"].startswith("4500x5400"))
check("wrong canvas fails file spec",
      qc.check_file_spec(Image.new("RGBA", (100, 100)), "x")["ok"] is False)

check("a solid slab fails coverage high",
      qc.check_coverage(Image.new("RGBA", (400, 400), (0, 0, 0, 255)))["ok"] is False)
check("an almost-empty file fails coverage low",
      qc.check_coverage(_art((400, 400), box=[190, 190, 210, 210]))["ok"] is False)
check("a mid-sized shape passes coverage",
      qc.check_coverage(_art((400, 400), box=[100, 100, 300, 300]))["ok"])

# Contrast is the check that caught the only real defect in the demo run.
dark = _art((400, 400), fill=(20, 20, 20))
light = _art((400, 400), fill=(238, 238, 238))
check("dark ink passes on white", qc.check_contrast(dark, "white")["ok"])
check("dark ink FAILS on black", qc.check_contrast(dark, "black")["ok"] is False)
check("light ink passes on black", qc.check_contrast(light, "black")["ok"])
check("light ink FAILS on white", qc.check_contrast(light, "white")["ok"] is False)
check("mid-tone garments are reported, never blocking",
      qc.check_contrast(dark, "sport grey", blocking=False)["ok"] is True
      and qc.check_contrast(dark, "sport grey", blocking=False)["reported_only"])

# The halo check went through two wrong versions; these pin the discriminator.
clean = _art((800, 800), box=[200, 200, 600, 600])
check("a clean hard edge reads as no halo",
      qc.check_halo(clean)["value"].startswith("ring 0%"))
haloed = clean.copy()
_a = haloed.getchannel("A").filter(ImageFilter.GaussianBlur(9))
haloed.putalpha(_a.point(lambda v: min(v, 110) if v < 250 else v))
check("a feathered fringe fills the ring",
      qc.check_halo(haloed)["value"].startswith("ring 100%"))
check("halo never blocks — the dense-linework confound is unresolved",
      qc.check_halo(haloed)["ok"] is True
      and qc.check_halo(haloed)["reported_only"])

bleeding = Image.new("RGBA", (400, 400), (0, 0, 0, 255))
check("ink at the boundary fails bleed", qc.check_bleed(bleeding)["ok"] is False)
check("ink inside the margin passes bleed",
      qc.check_bleed(_art((400, 400), box=[120, 120, 280, 280]))["ok"])

hairline = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
_d = ImageDraw.Draw(hairline)
for _x in range(40, 360, 8):
    _d.line([(_x, 40), (_x, 360)], fill=(0, 0, 0, 255), width=1)
check("hairlines fail the stroke check", qc.check_stroke(hairline)["ok"] is False)
check("a solid shape passes the stroke check", qc.check_stroke(clean)["ok"])

# Palette counts HUE clusters, not RGB — density varies lightness, not hue.
one_ink = compose.map_to_ink(gradient(200, 200), (200, 90, 30), autolevel=False)
check("one ink at many densities counts as one",
      qc.check_palette(one_ink, {"palette": {"inks": {"a": "#C85A1E"}}})["ok"])

check("a missing file is UNRUN, never a pass",
      qc.inspect("/nonexistent.png")["verdict"] == "unrun")
# Mid-grey clears 3:1 against BOTH white and black (relative luminance ~0.19,
# so 4.4:1 and 4.8:1), which is what lets the verdict turn on the unrun
# provenance check rather than on a contrast failure.
_tmp = "out/_test_art.png"
_art((4500, 5400), fill=(120, 120, 120), box=[1200, 1400, 3300, 4000]).save(
    _tmp, dpi=(300, 300))
_r = qc.inspect(_tmp, recipe=None)
check("no recipe leaves provenance UNRUN, never passed",
      _r["checks"]["provenance"]["ok"] is None and "provenance" in _r["unrun"])
check("an unrun check never yields a bare pass verdict",
      _r["verdict"] == "pass-with-unrun", _r["verdict"])

# ---------------------------------------------------------------- gate

print("\nthe v1 -> v2 gate")

import history as H
_led_backup = H.load()

check("an uninspected version has no record",
      H.inspection_for("__nonexistent__", 1) is None)

_real = H.load().get("designs", {}).get("proof-calavera")
if _real:
    check("demo left exactly two versions", len(_real["versions"]) == 2,
          str(len(_real["versions"])))
    check("v1 was blocked",
          any(i["version"] == 1 and i["verdict"] == "blocked"
              for i in _real["inspections"]))
    check("v2 passed",
          any(i["version"] == 2 and i["verdict"] == "pass"
              for i in _real["inspections"]))
    check("v2 records what changed",
          len([v for v in _real["versions"] if v["version"] == 2][0]["changes"]) >= 1)
    check("the gate found v1's inspection",
          H.inspection_for("proof-calavera", 1) is not None)
    a_ = [v for v in _real["versions"] if v["version"] == 1][0]["files"]["print"]
    b_ = [v for v in _real["versions"] if v["version"] == 2][0]["files"]["print"]
    hm = H.diff_heatmap(a_, b_)
    check("diff heatmap builds", hm is not None)
    # The first diff compared alpha only and reported 0.0% on a recolour.
    check("diff sees a recolour, not just movement", hm and hm[1] > 0.01,
          f"{hm[1]:.1%}" if hm else "none")
else:
    check("demo ledger present (run ./demo.sh first)", False)

# ---------------------------------------------------------------- force

print("\nthe force escape hatch")

# --force skips the gate. Having an escape hatch is reasonable; having a SILENT
# one was not. The flag was originally registered with argparse.SUPPRESS, so
# `--help` never mentioned it, and a forced v2 landed in the ledger looking
# exactly like an earned one. That quietly destroyed the only thing the ledger
# is for: a reader could no longer tell which v2 answered findings and which
# simply went around them. These checks pin the bypass as visible in --help,
# refused without a written reason, recorded, and shown in the report.

import contextlib
import io
import os as _os
import subprocess as _sp
import tempfile as _tempfile

import mockup

_HERE = _os.path.dirname(_os.path.abspath(__file__))


def _run_mockup(argv, ledger, out_dir):
    """Run mockup.main() against an ISOLATED ledger. Returns the exit code."""
    real_ledger, real_argv = H.LEDGER, sys.argv
    H.LEDGER = ledger
    sys.argv = ["mockup.py", "--out", out_dir] + argv
    try:
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            mockup.main()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    finally:
        H.LEDGER, sys.argv = real_ledger, real_argv


def _versions(ledger, design):
    import json as _json
    if not _os.path.exists(ledger):
        return []
    return _json.load(open(ledger))["designs"].get(design, {}).get("versions", [])


_sand = _tempfile.mkdtemp(prefix="force-")
_ledger = _os.path.join(_sand, "ledger.json")
_out = _os.path.join(_sand, "out")
_os.makedirs(_out, exist_ok=True)
_pf = _os.path.join(_sand, "print.png")
_art((900, 1080), fill=(30, 30, 30), box=[200, 240, 700, 840]).save(_pf)
_base = ["--design", "sandbox", "--print", _pf]

# An escape hatch nobody can see is a trapdoor. This is the check that would
# have failed against the original argparse.SUPPRESS registration.
_help = _sp.run([sys.executable, "mockup.py", "--help"], cwd=_HERE,
                capture_output=True, text=True).stdout
check("--force is documented in --help", "--force" in _help)
check("--force-reason is documented in --help", "--force-reason" in _help)
check("--help says what --force skips", "inspection" in _help.lower())

# The default path must be untouched by the existence of force.
check("v2 is still refused with no inspection of v1",
      _run_mockup(_base + ["--version", "2"], _ledger, _out) == 3)
check("a refused v2 writes nothing to the ledger",
      _versions(_ledger, "sandbox") == [])

check("v1 needs no gate", _run_mockup(_base + ["--version", "1"], _ledger, _out) == 0)
check("v1 was recorded", len(_versions(_ledger, "sandbox")) == 1)
check("an earned version carries no forced marker",
      "forced" not in _versions(_ledger, "sandbox")[0])

# Force without a reason is refused — and refused with its own exit code, so a
# caller can tell "you did not justify this" apart from "the gate stopped you".
check("--force alone is refused",
      _run_mockup(_base + ["--version", "2", "--force"], _ledger, _out) == 4)
check("--force with blank whitespace is refused",
      _run_mockup(_base + ["--version", "2", "--force", "--force-reason", "   "],
                  _ledger, _out) == 4)
check("refusing to force writes nothing to the ledger",
      len(_versions(_ledger, "sandbox")) == 1)
check("the force refusal is distinct from the gate refusal", 4 != 3)

# With a reason, it goes through where the gate would otherwise have refused.
_reason = "printer needed the file before the inspector was free"
check("--force with a reason builds a v2 the gate would have refused",
      _run_mockup(_base + ["--version", "2", "--force",
                           "--force-reason", _reason], _ledger, _out) == 0)
_v2 = [v for v in _versions(_ledger, "sandbox") if v["version"] == 2]
check("the forced version was recorded", len(_v2) == 1)
check("the ledger marks it forced", _v2 and _v2[0].get("forced") is True)
check("the ledger keeps the stated reason",
      _v2 and _v2[0].get("force_reason") == _reason)

# Forcing does not excuse --change: the record still has to say what moved.
check("forcing still records changes when given",
      _run_mockup(_base + ["--version", "3", "--force", "--force-reason", _reason,
                           "--change", "raised gamma"], _ledger, _out) == 0
      and [v for v in _versions(_ledger, "sandbox")
           if v["version"] == 3][0]["changes"] == ["raised gamma"])

# And a reader scanning the report has to SEE it, not find it in JSON.
import json as _json
_rep = H.build_report(_json.load(open(_ledger)), _out)
_html = open(_rep).read()
check("the report marks the forced version", "Gate bypassed" in _html)
check("the report shows the stated reason", _reason in _html)
check("the forced marker uses the blocked-red style", 'class="forced"' in _html)
check("an earned version is not marked as bypassed",
      _html.count("Gate bypassed") == 2, str(_html.count("Gate bypassed")))

_shutil_rmtree_ok = True
try:
    import shutil as _shutil
    _shutil.rmtree(_sand)
except Exception:
    _shutil_rmtree_ok = False
check("the real ledger was never touched by the force tests",
      H.LEDGER.endswith(_os.path.join("out", "history.json"))
      and H.load() == _led_backup)

# ---------------------------------------------------------------- result

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all checks passed")
