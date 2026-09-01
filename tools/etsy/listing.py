#!/usr/bin/env python3
"""
listing.py — build and validate an Etsy listing. Searchability, enforced.

Every convention here is already proven on disk in ETSY-ITEM6-DRAFT.md and
ETSY-ITEMS-2-7-WALKTHROUGH.md. This file does not invent a strategy; it stops
the four listings' worth of hard-won rules from being forgotten on listing five.

WHAT IT CHECKS, AND WHY EACH ONE COSTS MONEY
    Title over 140          Etsy truncates. The tail is wasted.
    Phrase after char 40    Etsy search shows ~40-50 chars, Google 50-60. A
                            distinctive phrase past that is invisible where it
                            counts.
    Fewer than 13 tags      "An empty slot is reach you declined."
    Tag over 20 chars       Etsy rejects it.
    Single-word tags        "Nobody searches 'tee'."
    Near-twin tags          'graphic tee' and 'graphic tees' compete for one
                            slot's worth of reach.
    Cannibalisation         Two of YOUR listings sharing tags fight each other
                            in search. This is the trap ETSY-LISTING-COPY.md
                            names, and the only check here that needs the whole
                            catalogue to run.
    Banned words            The standing list from Prompts/school-genius.md.
    Margin                  Against the REAL $9.79 cost, not the $13.55 still
                            sitting in Prompts/etsy-listing.md.

USAGE
    python3 listing.py --catalogue catalogue.json --id orchid-skull
    python3 listing.py --catalogue catalogue.json --all        # every listing
    python3 listing.py --catalogue catalogue.json --check-only
    python3 listing.py --price 23.99 --margin-only
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

TITLE_MAX = 140
TITLE_VISIBLE = 40          # what survives Etsy search truncation
TAG_MAX_CHARS = 20
TAG_COUNT = 13

# True of any shirt in this shop. Six of the thirteen, so seven stay free for
# the design. ETSY-ITEM6-DRAFT.md:100-109.
UNIVERSAL_TAGS = [
    "unisex graphic tee",
    "made to order shirt",
    "heavy cotton tshirt",
    "printed in usa tee",
    "gift for him",
    "gift for her",
]

# CorpalCaptain_Margin_Calculator.xlsx, verified against Printify 2026-08-15.
# Fees are charged on retail PLUS shipping, not retail alone — the mistake that
# made the old numbers wrong.
COST = 9.79                 # SwiftPOD Gildan 5000, flat S-XL
SHIP_CHARGED = 4.75         # buyer pays; passed straight to Printify, nets zero
LISTING_FEE = 0.20
TXN_RATE = 0.065
PROC_RATE = 0.03
PROC_FIXED = 0.25
OFFSITE_ADS_RATE = 0.15     # under $10k lifetime; opted out

# Prompts/school-genius.md:11 — the canonical copy. A second, slightly different
# list exists in Design/CHECKPOINT.md; this one is the version the backend's
# schoolgenius mode implements.
BANNED = [
    "additionally", "align with", "boasts", "bolstered", "crucial", "delve",
    "emphasizing", "enduring", "enhance", "fostering", "garner", "highlight",
    "highlights", "interplay", "intricate", "intricacies", "key", "landscape",
    "meticulous", "meticulously", "pivotal", "showcase", "tapestry", "testament",
    "underscore", "valuable", "vibrant", "nested", "groundbreaking", "renowned",
    "diverse array", "rich heritage", "natural beauty", "commitment to",
]

# Not on the banned list but banned by the shop's own register.
VOICE_FLAGS = ["quality", "premium", "best-selling", "amazing", "stunning",
               "perfect for anyone", "high quality"]


# ---------------------------------------------------------------- margin

def margin(retail, offsite_ads=False):
    """Reproduces the margin calculator exactly. Verified cell by cell."""
    buyer_pays = retail + SHIP_CHARGED
    fees = (LISTING_FEE + buyer_pays * TXN_RATE
            + buyer_pays * PROC_RATE + PROC_FIXED)
    if offsite_ads:
        fees += buyer_pays * OFFSITE_ADS_RATE
    keep = retail - COST - fees
    return {"retail": retail, "buyer_pays": buyer_pays, "fees": fees,
            "keep": keep, "margin_pct": 100 * keep / retail if retail else 0}


def break_even():
    rate = TXN_RATE + PROC_RATE
    return (COST + LISTING_FEE + PROC_FIXED + SHIP_CHARGED * rate) / (1 - rate)


# ---------------------------------------------------------------- validators

def _norm(tag):
    """Singularise and strip so near-twins collide."""
    t = re.sub(r"[^a-z0-9 ]", "", tag.lower()).strip()
    return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") else w for w in t.split())


# Words that name the product rather than the subject. Stripping them exposes
# the search a tag is actually going after.
PRODUCT_WORDS = {"tee", "tees", "tshirt", "tshirts", "shirt", "shirts", "gift",
                 "gifts", "art", "apparel", "print", "prints", "top", "clothing"}


def _head(tag):
    """The subject of a tag, with the product word removed."""
    words = _norm(tag).split()
    while words and words[-1] in PRODUCT_WORDS:
        words.pop()
    return " ".join(words)


def check_title(title, phrase):
    out = []
    n = len(title)
    if n > TITLE_MAX:
        out.append(("error", f"title is {n} chars, cap is {TITLE_MAX} — the tail is cut"))
    if phrase:
        pos = title.lower().find(phrase.lower())
        if pos < 0:
            out.append(("error", f"the distinctive phrase '{phrase}' is not in the title"))
        elif pos + len(phrase) > TITLE_VISIBLE:
            out.append(("warn", f"'{phrase}' ends at char {pos + len(phrase)}; Etsy "
                                f"search shows about {TITLE_VISIBLE}. Move it earlier."))
    if "  " in title:
        out.append(("warn", "double space in the title"))
    if title != title.strip():
        out.append(("warn", "title has leading or trailing whitespace"))
    return out


def check_tags(tags):
    out = []
    if len(tags) != TAG_COUNT:
        lvl = "error" if len(tags) > TAG_COUNT else "warn"
        out.append((lvl, f"{len(tags)} tags, want exactly {TAG_COUNT} — "
                         f"an empty slot is reach you declined"))
    seen = {}
    for t in tags:
        if len(t) > TAG_MAX_CHARS:
            out.append(("error", f"tag '{t}' is {len(t)} chars, cap is {TAG_MAX_CHARS}"))
        if len(t.split()) == 1:
            out.append(("warn", f"tag '{t}' is one word — nobody searches single words"))
        k = _norm(t)
        if k in seen:
            out.append(("error", f"tags '{seen[k]}' and '{t}' are near-twins; they "
                                 f"compete for one slot's worth of reach"))
        seen[k] = t
    return out


def check_cannibalisation(this_id, tags, catalogue, threshold=3):
    """
    Two of your own listings sharing tags fight each other in Etsy search.

    ETSY-LISTING-COPY.md:99-104 solved this by hand for the two jellyfish — blue
    leans ocean/dark academia, gold leans naturalist/vintage plate. This makes it
    a check instead of a memory.

    Universal tags are excluded: all thirteen listings share those by design.
    """
    out = []
    uni = {_norm(t) for t in UNIVERSAL_TAGS}
    uni_h = {_head(t) for t in UNIVERSAL_TAGS}
    mine = {_norm(t) for t in tags} - uni
    mine_h = {_head(t) for t in tags} - uni_h - {""}

    for other in catalogue.get("designs", []):
        if other.get("id") == this_id:
            continue
        theirs = {_norm(t) for t in other.get("tags", [])} - uni
        shared = mine & theirs
        if len(shared) >= threshold:
            out.append(("warn", f"shares {len(shared)} design tags with "
                                f"'{other.get('id')}' ({', '.join(sorted(shared))}) — "
                                f"they will compete in search. Lean them apart."))
            continue

        # Exact-match alone misses the commonest real collision: 'dark academia
        # tee' and 'dark academia shirt' are different strings competing for the
        # same search. Compare with the product word stripped too.
        theirs_h = {_head(t) for t in other.get("tags", [])} - uni_h - {""}
        shared_h = (mine_h & theirs_h) - {_norm(s) for s in shared}
        if len(shared_h) >= threshold:
            out.append(("warn", f"shares {len(shared_h)} tag subjects with "
                                f"'{other.get('id')}' ({', '.join(sorted(shared_h))}) — "
                                f"different wording, same search. Lean them apart."))
    return out


def check_words(text, label):
    out = []
    low = text.lower()
    for w in BANNED:
        if re.search(rf"\b{re.escape(w)}\b", low):
            out.append(("error", f"{label}: banned word '{w}'"))
    for w in VOICE_FLAGS:
        if re.search(rf"\b{re.escape(w)}\b", low):
            out.append(("warn", f"{label}: '{w}' is off-register for this shop"))
    return out


# ---------------------------------------------------------------- build

BODY = """Printed on a Gildan 5000 Heavy Cotton tee — unisex sizing, 5.3 oz cotton, seamless collar, taped neck and shoulders, double-needle hems. It fits like a standard men's tee; if you want it roomy, size up one.

Made when you order it. Nothing sits in a warehouse. Your shirt is printed after you buy it, which takes a few business days before it ships — the tradeoff for not having a stockroom full of guesses.

If it arrives wrong, I replace it free. Damaged, misprinted, or defective: send a photo and a replacement goes out. No return shipping, no argument.

What I do not take back is a size that did not fit or a change of mind. A made-to-order shirt cannot be restocked, so please check the measurements before ordering. The size chart is on this listing and I answer sizing questions before you buy — ask me.

Printed and shipped from the United States by SwiftPOD, my declared production partner. Designed by me in Connecticut."""


def build_description(design_paragraph):
    """Structure B. Only the design paragraph changes per listing."""
    return design_paragraph.strip() + "\n\n" + BODY


def build_tags(design_tags):
    return list(design_tags) + UNIVERSAL_TAGS


# ---------------------------------------------------------------- report

def report(design, catalogue, quiet=False):
    issues = []
    title = design.get("title", "")
    phrase = design.get("phrase", "")
    tags = build_tags(design.get("tags", []))
    desc = build_description(design.get("design_paragraph", ""))

    issues += check_title(title, phrase)
    issues += check_tags(tags)
    issues += check_cannibalisation(design.get("id"), tags, catalogue)
    issues += check_words(title, "title")
    issues += check_words(desc, "description")

    price = design.get("price", 23.99)
    m = margin(price)
    if m["keep"] <= 0:
        issues += [("error", f"at ${price:.2f} you lose ${-m['keep']:.2f} per shirt; "
                             f"break-even is ${break_even():.2f}")]
    elif price < break_even() + 3:
        issues += [("warn", f"${price:.2f} is close to the ${break_even():.2f} "
                            f"break-even — little room for a discount or an ad")]

    if not quiet:
        print(f"\n{'='*72}\n{design.get('id')} — {design.get('name','')}\n{'='*72}")
        print(f"\nTITLE ({len(title)}/{TITLE_MAX})\n  {title}")
        print(f"\nTAGS ({len(tags)}/{TAG_COUNT})")
        for t in tags:
            mark = "univ" if t in UNIVERSAL_TAGS else "    "
            print(f"  {mark}  {t:<22} {len(t):>2}")
        print(f"\nDESCRIPTION ({len(desc)} chars, first 160 are the search snippet)")
        print("  " + desc[:160].replace("\n", " ") + "…")
        print(f"\nMARGIN at ${price:.2f}")
        print(f"  buyer pays ${m['buyer_pays']:.2f} · fees ${m['fees']:.2f} · "
              f"you keep ${m['keep']:.2f} ({m['margin_pct']:.1f}%)")
        print(f"  break-even ${break_even():.2f} · "
              f"{round(1000 / m['keep']) if m['keep'] > 0 else '—'} shirts for $1,000")

        errs = [i for i in issues if i[0] == "error"]
        warns = [i for i in issues if i[0] == "warn"]
        if not issues:
            print("\nCHECKS  all clear")
        else:
            print(f"\nCHECKS  {len(errs)} error, {len(warns)} warning")
            for lvl, msg in issues:
                print(f"  {'ERROR' if lvl == 'error' else 'warn '}  {msg}")
    return issues


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalogue", default=os.path.join(HERE, "catalogue.json"))
    ap.add_argument("--id", help="one design id")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check-only", action="store_true", help="issues only, no copy")
    ap.add_argument("--margin-only", action="store_true")
    ap.add_argument("--price", type=float, default=23.99)
    a = ap.parse_args()

    if a.margin_only:
        print(f"cost ${COST:.2f} · shipping ${SHIP_CHARGED:.2f} charged and passed through")
        print(f"break-even ${break_even():.2f}\n")
        print(f"{'retail':>8}{'buyer':>9}{'fees':>8}{'keep':>8}{'margin':>9}{'+ads keep':>11}")
        for r in (22.99, 23.99, 24.99, a.price):
            m, ma = margin(r), margin(r, offsite_ads=True)
            print(f"{r:>8.2f}{m['buyer_pays']:>9.2f}{m['fees']:>8.2f}"
                  f"{m['keep']:>8.2f}{m['margin_pct']:>8.1f}%{ma['keep']:>11.2f}")
        return

    if not os.path.exists(a.catalogue):
        sys.exit(f"no catalogue at {a.catalogue}")
    cat = json.load(open(a.catalogue))

    designs = cat.get("designs", [])
    if a.id:
        designs = [d for d in designs if d.get("id") == a.id]
        if not designs:
            sys.exit(f"no design with id '{a.id}'")
    elif not a.all:
        sys.exit("need --id, --all, or --margin-only")

    total_err = 0
    for d in designs:
        issues = report(d, cat, quiet=a.check_only)
        errs = [i for i in issues if i[0] == "error"]
        total_err += len(errs)
        if a.check_only and issues:
            print(f"{d.get('id')}: {len(errs)} error, "
                  f"{len(issues) - len(errs)} warning")
            for lvl, msg in issues:
                print(f"  {'ERROR' if lvl == 'error' else 'warn '}  {msg}")

    if total_err:
        print(f"\n{total_err} error(s) — fix before listing.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
