#!/usr/bin/env python3
"""
schedule.py — two calendars from one catalogue.

  1. RELEASE  which design goes live on Etsy on which day.
  2. POSTING  one Pinterest or TikTok slot per day, at varied times.

WHY RELEASES ARE STAGGERED AND NOT BULK
    Etsy gives a new listing a temporary visibility boost. Uploading eight in one
    afternoon spends that boost once; spacing them earns it eight times. And
    under the August 2026 Creativity Standards, a sudden burst of near-identical
    listings is the pattern that reads as undifferentiated bulk output — an
    explicit deactivation trigger. Slow is both better ranked and safer.

    Everything must be live by the OCT 15 cutoff. A listing needs roughly six
    weeks of ranking history before the December peak, and December is where the
    money in this window actually is.

WHY THESE POSTING TIMES
    Pinterest 2026 engagement data: Tue-Thu 10:00-13:00 is the primary band;
    Sat 08:00-11:00 and weekday 20:00-23:00 are secondary; Fri and Sat carry the
    highest save rates. A new pin's first 24-48 hours decide how widely Pinterest
    distributes it afterwards, so the slot matters more here than on most
    platforms.

    TikTok slots are HANDS ONLY — the cutout on screen, the layer reveal, the
    mockup, the parcel. Never a face. That is a standing constraint, not a
    stylistic preference.

WHAT IT AVOIDS
    The school wall: no slot between 09-13 and 09-29, where twelve graded
    deadlines fall, six of them on 09-20 alone.

USAGE
    python3 schedule.py --catalogue catalogue.json
    python3 schedule.py --start 2026-09-05 --end 2026-11-30 --ics
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Twelve graded deadlines fall in here, six of them on 09-20. Protected.
BLACKOUT = (dt.date(2026, 9, 13), dt.date(2026, 9, 29))

# Everything live by here: ~6 weeks of ranking history before December.
RELEASE_CUTOFF = dt.date(2026, 10, 15)

# Pinterest bands, from the 2026 engagement data. (weekday, hour, minute, weight)
# weekday: Mon=0. Higher weight = used sooner in the rotation.
PIN_SLOTS = [
    (1, 10, 30, 3), (2, 11, 0, 3), (3, 10, 0, 3),      # Tue-Thu primary band
    (4, 20, 30, 2), (5, 9, 0, 3), (5, 20, 0, 2),       # Fri/Sat — best save rates
    (6, 10, 30, 2), (0, 21, 0, 1), (1, 20, 30, 1),     # Sun + weekday evenings
    (2, 21, 30, 1), (3, 20, 0, 1), (4, 11, 30, 2),
]

# Hands-only. Each is a shot you can film without appearing in it.
TIKTOK_ANGLES = [
    "layer reveal — sources fading in one at a time until the composite lands",
    "the cutout — paper ground lifting away from the plate, before and after",
    "ink unify — three differently-toned sources snapping to one palette",
    "silhouette test — the design flattened to black, does it read across a room",
    "mockup drop — the file landing on the garment, four colourways",
    "parcel — hands folding and sleeving the sample, no face",
    "source hunt — scrolling the archive page, cursor only",
    "scale check — holding the print area against the shirt front",
]

PIN_ANGLES = [
    "the design, full front, on the light garment",
    "detail crop — the part that rewards a close look",
    "on-body mockup, squared for the mobile crop",
    "the source plates side by side with the finished composite",
    "what it is made from — the two archives named",
    "flat lay against a plain ground",
    "the dark-garment colourway",
    "seasonal angle — why this one now",
]


def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def in_blackout(d):
    return BLACKOUT[0] <= d <= BLACKOUT[1]


def release_schedule(designs, start, cutoff=RELEASE_CUTOFF):
    """
    Spread the unreleased designs over the usable days before the cutoff.

    Seasonal designs are pulled earlier so they are ranking before their peak
    rather than launching into it.
    """
    pending = [d for d in designs if d.get("status") != "live"]
    if not pending:
        return []

    # Seasonal first — they have a date they must beat.
    def key(d):
        return (0 if d.get("seasonal_peak") else 1, d.get("id", ""))
    pending = sorted(pending, key=key)

    # Weekends first — that is when the work actually happens. But there are only
    # seven usable weekend days between a September start and the Oct 15 cutoff
    # once the school wall is removed, and eight designs. Falling back to
    # weekdays is what stops two releases landing on one day, which would spend
    # one visibility boost instead of two and defeat the whole point.
    weekend = [d for d in daterange(start, cutoff)
               if not in_blackout(d) and d.weekday() in (5, 6)]
    weekday = [d for d in daterange(start, cutoff)
               if not in_blackout(d) and d.weekday() not in (5, 6)]

    usable = weekend if len(weekend) >= len(pending) else sorted(weekend + weekday)
    if not usable:
        return [(None, d) for d in pending]

    # Spread evenly across whatever is available, and never reuse a date.
    out, used = [], set()
    n = len(pending)
    for k, d in enumerate(pending):
        want = min(len(usable) - 1, round(k * (len(usable) - 1) / max(1, n - 1))) \
            if n > 1 else 0
        while want < len(usable) and usable[want] in used:
            want += 1
        if want >= len(usable):                      # walk back if we ran off the end
            want = next((i for i in range(len(usable) - 1, -1, -1)
                         if usable[i] not in used), None)
        if want is None:
            out.append((None, d))
        else:
            used.add(usable[want])
            out.append((usable[want], d))
    return sorted(out, key=lambda t: (t[0] is None, t[0]))


def posting_schedule(designs, start, end):
    """One slot a day. Platform alternates; angle and design rotate."""
    slots = []
    pin_i = tik_i = des_i = 0
    pin_by_day = {}
    for wd, h, m, w in PIN_SLOTS:
        pin_by_day.setdefault(wd, []).append((h, m, w))
    for wd in pin_by_day:
        pin_by_day[wd].sort(key=lambda t: -t[2])

    for day in daterange(start, end):
        if in_blackout(day):
            continue
        design = designs[des_i % len(designs)]
        des_i += 1

        # Pinterest carries most of the load; it is a search engine rather than a
        # feed, so a pin keeps working for months. TikTok every third day.
        if day.toordinal() % 3 == 0:
            angle = TIKTOK_ANGLES[tik_i % len(TIKTOK_ANGLES)]
            tik_i += 1
            hour, minute = (19, 30) if day.weekday() < 5 else (12, 0)
            slots.append({"date": day, "time": (hour, minute), "platform": "TikTok",
                          "design": design, "angle": angle})
        else:
            cands = pin_by_day.get(day.weekday()) or [(11, 0, 1)]
            h, m, _ = cands[pin_i % len(cands)]
            pin_i += 1
            angle = PIN_ANGLES[pin_i % len(PIN_ANGLES)]
            slots.append({"date": day, "time": (h, m), "platform": "Pinterest",
                          "design": design, "angle": angle})
    return slots


def to_markdown(releases, slots, tz):
    L = []
    L.append("# Release and posting calendar\n")
    L.append(f"Times are local ({tz}). Nothing falls between "
             f"{BLACKOUT[0]} and {BLACKOUT[1]} — that is the school wall.\n")

    L.append("\n## Releases — when each design goes live on Etsy\n")
    L.append("Staggered on purpose. Etsy's new-listing boost is spent once per "
             "upload, so spacing earns it repeatedly; and a burst of similar "
             "listings reads as bulk output under the current Creativity "
             "Standards.\n")
    L.append("| Date | Design | Why then |")
    L.append("|---|---|---|")
    for date, d in releases:
        why = d.get("seasonal_note") or "spread for the ranking boost"
        L.append(f"| {date if date else '**no slot left**'} | {d.get('name')} | {why} |")
    L.append(f"\nAll live by **{RELEASE_CUTOFF}** — roughly six weeks of ranking "
             f"history before the December peak.\n")

    L.append("\n## Posting — one slot a day\n")
    cur = None
    for s in slots:
        wk = s["date"].isocalendar()[1]
        if wk != cur:
            cur = wk
            L.append(f"\n### Week {wk} — from {s['date']}\n")
            L.append("| Date | Day | Time | Platform | Design | Shot |")
            L.append("|---|---|---|---|---|---|")
        h, m = s["time"]
        L.append(f"| {s['date']} | {s['date'].strftime('%a')} | {h:02d}:{m:02d} | "
                 f"{s['platform']} | {s['design'].get('name')} | {s['angle']} |")
    L.append("\n---\n")
    L.append("TikTok slots are hands-only by standing constraint — the screen, "
             "the plates, the parcel. Never a face.\n")
    return "\n".join(L)


def to_ics(releases, slots, tz):
    """Minimal valid iCalendar. Floating local times, no VTIMEZONE."""
    def esc(s):
        return (str(s).replace("\\", "\\\\").replace(";", r"\;")
                .replace(",", r"\,").replace("\n", r"\n"))

    def uid(*parts):
        return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:20]

    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0",
         "PRODID:-//CorpalCaptain//shirt pipeline//EN", "CALSCALE:GREGORIAN",
         f"X-WR-CALNAME:CorpalCaptain releases and posts", f"X-WR-TIMEZONE:{tz}"]

    for date, d in releases:
        if not date:
            continue
        L += ["BEGIN:VEVENT", f"UID:{uid('rel', d.get('id'), date)}@corpalcaptain",
              f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{date.strftime('%Y%m%d')}",
              f"DTEND;VALUE=DATE:{(date + dt.timedelta(days=1)).strftime('%Y%m%d')}",
              f"SUMMARY:{esc('LIST: ' + str(d.get('name')))}",
              f"DESCRIPTION:{esc('Publish on Etsy. Run listing.py first.')}",
              "END:VEVENT"]

    for s in slots:
        h, m = s["time"]
        start = dt.datetime.combine(s["date"], dt.time(h, m))
        end = start + dt.timedelta(minutes=20)
        L += ["BEGIN:VEVENT",
              f"UID:{uid('post', s['platform'], s['date'], h, m)}@corpalcaptain",
              f"DTSTAMP:{stamp}",
              f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
              f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
              f"SUMMARY:{esc(s['platform'] + ': ' + str(s['design'].get('name')))}",
              f"DESCRIPTION:{esc(s['angle'])}", "END:VEVENT"]

    L.append("END:VCALENDAR")
    return "\r\n".join(L) + "\r\n"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalogue", default=os.path.join(HERE, "catalogue.json"))
    ap.add_argument("--start", default="2026-09-05")
    ap.add_argument("--end", default="2026-11-30")
    ap.add_argument("--tz", default="America/New_York")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--ics", action="store_true", help="also write an .ics")
    a = ap.parse_args()

    if not os.path.exists(a.catalogue):
        sys.exit(f"no catalogue at {a.catalogue}")
    cat = json.load(open(a.catalogue))
    designs = cat.get("designs", [])
    if not designs:
        sys.exit("catalogue has no designs")

    start = dt.date.fromisoformat(a.start)
    end = dt.date.fromisoformat(a.end)
    if end < start:
        sys.exit("--end is before --start")

    releases = release_schedule(designs, start)
    slots = posting_schedule(designs, start, end)

    os.makedirs(a.out, exist_ok=True)
    md = os.path.join(a.out, "calendar.md")
    open(md, "w").write(to_markdown(releases, slots, a.tz))
    print(f"wrote {md}")

    if a.ics:
        ics = os.path.join(a.out, "calendar.ics")
        open(ics, "w").write(to_ics(releases, slots, a.tz))
        print(f"wrote {ics}")

    late = [(d, x) for d, x in releases if d is None or d > RELEASE_CUTOFF]
    print(f"\n{len(releases)} releases, {len(slots)} posting slots, "
          f"{(end - start).days + 1} days spanned")
    if late:
        print(f"⚠ {len(late)} release(s) fall after the {RELEASE_CUTOFF} cutoff: "
              f"{', '.join(str(x.get('id')) for _, x in late)}", file=sys.stderr)
    else:
        print(f"all releases land on or before the {RELEASE_CUTOFF} cutoff")


if __name__ == "__main__":
    main()
