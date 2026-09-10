#!/usr/bin/env python3
"""
scrub_check.py — refuse to let an identifier reach the published tree.

WHY THIS EXISTS
    Nothing in trackA/ could fail before this file. The extraction's own scrub
    was a one-time reading pass, so its result decayed the moment anyone edited
    a mockup. A check that runs is worth more than a checklist that was read.

WHAT IT CHECKS
    Every file under the PUBLISHED subtrees (HUDKit/ and mockups/) against the
    patterns in _private/identifiers.txt — a person, a town, a school, a real
    timetable, the private app and its siblings, hardware, personal metrics,
    third-party marks, and the generic leak shapes (home paths, emails, team
    ids, loopback addresses).

    Plus two things a literal list cannot express:
      - first- and second-person voice, which marks a file as private
        correspondence even when every noun in it is clean;
      - the wordmark glyph table's coverage, because a partial alphabet is a
        set-by-omission that fingerprints whatever words the original needed.

WHY THE PATTERNS LIVE IN _private/
    A checker that carries the literal strings is itself the leak. This file is
    safe to read; its input is not, and its input never ships.

USAGE
    python3 scrub_check.py            # from trackA/
    python3 scrub_check.py --list     # show what is being checked, no scan
    exit 0 clean · exit 1 hits found · exit 2 cannot run
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATTERNS_FILE = os.path.join(HERE, "_private", "identifiers.txt")

# Only these subtrees are published; everything else in trackA/ stays behind.
PUBLISHED = ("HUDKit", "mockups")

SKIP_DIRS = {".git", ".build", "node_modules", "__pycache__", ".swiftpm"}
TEXT_EXT = {".swift", ".html", ".md", ".css", ".js", ".json", ".txt", ".yml", ".yaml"}

# Voice. A package's documentation speaks about the code; a design review speaks
# to a person. The second is a private artifact no matter how clean its nouns.
VOICE = [
    ("first person", re.compile(r"(?<![\w'])(I|I'm|I've|I'd|I'll|my|mine)(?![\w'])")),
    ("second person", re.compile(r"(?<![\w'])(you|your|yours|you're|you've)(?![\w'])", re.I)),
]

# Doc comments legitimately say "your app" when addressing the consumer, so the
# second-person rule is enforced only where the voice should be impersonal.
VOICE_SCOPE = ("mockups",)


def load_patterns(path):
    if not os.path.exists(path):
        sys.exit(f"cannot run: {path} is missing.\n"
                 f"It holds the literal identifiers and is deliberately not "
                 f"published. Restore it from the private tree.")
    out = []
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("re:"):
            body = line[3:]
            try:
                out.append((line, re.compile(body, re.I)))
            except re.error as e:
                sys.exit(f"cannot run: bad regex on line {n} of {path}: {e}")
        else:
            out.append((line, re.compile(re.escape(line), re.I)))
    if not out:
        sys.exit(f"cannot run: {path} defines no patterns.")
    return out


def files_to_scan():
    for sub in PUBLISHED:
        root_dir = os.path.join(HERE, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, names in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in sorted(names):
                ext = os.path.splitext(name)[1].lower()
                if ext and ext not in TEXT_EXT:
                    continue
                yield os.path.join(root, name)


def glyph_coverage():
    """The alphabet the wordmark can actually draw.

    Reported, not merely counted: a table that covers only the letters some
    private word needed is an identifier, and the gap list is what says so.
    """
    path = os.path.join(HERE, "HUDKit", "Sources", "HUDKit", "BlockLetters.swift")
    if not os.path.exists(path):
        return None, None
    src = open(path, encoding="utf-8").read()
    keys = set(re.findall(r'^\s*"(.)"\s*:\s*\[', src, re.M))
    want = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return sorted(want - keys), sorted(keys)



MONTHS = {m: i for i, m in enumerate(
    "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), 1)}
FULL_MONTHS = {m.upper(): i for i, m in enumerate(
    "January February March April May June July August September October "
    "November December".split(), 1)}
DAYS = "MON TUE WED THU FRI SAT SUN".split()
FULL_DAYS = [d.upper() for d in
             "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()]

# "MON 8 JUN", "MONDAY 8 JUNE", "TUE 25 AUG"
DATED = re.compile(
    r"\b(MON|TUE|WED|THU|FRI|SAT|SUN)[A-Z]*\s+(\d{1,2})\s+"
    r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\b", re.I)


def calendar_errors(year=2026):
    """Weekday labels that do not match the real weekday of the date.

    A mockup that says "WED 10 JUN" when the tenth is a Thursday is not a
    leak, but it is the fingerprint of a half-finished scrub: someone changed
    the dates a reader can see and left the ones encoded elsewhere. It is
    also, on its own, the kind of error that makes a design study look wrong.
    """
    import datetime
    out = []
    for path in files_to_scan():
        rel = os.path.relpath(path, HERE)
        try:
            lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for m in DATED.finditer(line):
                dname, day, mon = m.group(1).upper(), int(m.group(2)), m.group(3).upper()
                try:
                    real = datetime.date(year, MONTHS[mon], day)
                except ValueError:
                    out.append((rel, n, m.group(0), f"no such date in {year}"))
                    continue
                want = DAYS[real.weekday()]
                if want != dname:
                    out.append((rel, n, m.group(0),
                                f"{day} {mon} {year} is a {want}, not {dname}"))
    return out


def main():
    patterns = load_patterns(PATTERNS_FILE)

    if "--list" in sys.argv:
        print(f"{len(patterns)} identifier patterns from {PATTERNS_FILE}")
        print(f"published subtrees: {', '.join(PUBLISHED)}")
        print(f"voice rules enforced under: {', '.join(VOICE_SCOPE)}")
        return 0

    hits = []
    scanned = 0
    for path in files_to_scan():
        scanned += 1
        rel = os.path.relpath(path, HERE)
        try:
            lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        except OSError as e:
            hits.append((rel, 0, "unreadable", str(e)))
            continue
        in_voice_scope = rel.split(os.sep)[0] in VOICE_SCOPE
        for n, line in enumerate(lines, 1):
            for label, rx in patterns:
                m = rx.search(line)
                if m:
                    hits.append((rel, n, label, m.group(0)))
            if in_voice_scope:
                for label, rx in VOICE:
                    m = rx.search(line)
                    if m:
                        hits.append((rel, n, label, m.group(0)))

    missing, have = glyph_coverage()
    cal = calendar_errors()

    print(f"scrub_check: {scanned} published files, {len(patterns)} patterns")
    if missing is not None:
        if missing:
            print(f"\nGLYPH TABLE INCOMPLETE — {len(have)} of 36 characters.")
            print(f"  missing: {''.join(missing)}")
            print("  A partial alphabet is a set-by-omission: it says which "
                  "letters the\n  original wordmark needed. Draw the rest.")
        else:
            print("glyph table: complete (A-Z 0-9), carries no information")

    if cal:
        print(f"\nCALENDAR INCOHERENT — {len(cal)} weekday label(s) do not "
              f"match the date:")
        for rel, n, text, why in cal:
            print(f"  {rel}:{n}  {text!r}  {why}")
    else:
        print("calendar: every weekday label matches its date")

    if hits:
        print(f"\n{len(hits)} HIT(S):\n")
        for rel, n, label, text in hits:
            print(f"  {rel}:{n}  [{label}]  {text!r}")
        print("\nFAIL — the published tree is not clean.")
        return 1

    if missing or cal:
        return 1

    print("\nPASS — no identifier reaches the published tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
