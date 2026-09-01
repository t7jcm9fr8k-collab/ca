#!/usr/bin/env python3
"""
history.py — the append-only ledger, and the change history you can look at.

WHY APPEND-ONLY
    A version is never edited in place. That is the whole difference between a
    history and a state: if v1's inspection could be overwritten when v2 is
    built, there would be no record that v2 was ever needed, and the gate would
    become a formality.

WHAT IT HOLDS
    Per design: every version with its files and the changes made, and every
    inspection with all nine check numbers. Nothing is ever removed.

WHAT IT PRODUCES
    `out/history.html` — v1 mockups, the inspection table with failed numbers in
    red, what changed and why, v2 beside v1, and a pixel-difference heatmap so
    the change is visible rather than described.

    A diff heatmap matters more than it sounds. "Raised gamma to 0.85" is a
    sentence; the heatmap shows you the tentacles thickened and nothing else
    moved, which is the thing you actually wanted to confirm.

USAGE
    python3 history.py --report
    python3 history.py --show orchid-skull
"""

import argparse
import base64
import datetime as dt
import io
import json
import os
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "out", "history.json")


# ---------------------------------------------------------------- ledger

def _now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load():
    if os.path.exists(LEDGER):
        try:
            return json.load(open(LEDGER))
        except Exception:
            pass
    return {"designs": {}}


def save(led):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as f:
        json.dump(led, f, indent=2)
    os.replace(tmp, LEDGER)          # atomic; a half-written ledger is worse than none


def _design(led, design):
    return led["designs"].setdefault(design, {"versions": [], "inspections": []})


def record_version(design, version, files, changes=None, note=""):
    led = load()
    d = _design(led, design)
    d["versions"].append({
        "version": version, "at": _now(), "files": files,
        "changes": changes or [], "note": note,
    })
    save(led)


def record_inspection(design, version, result):
    led = load()
    d = _design(led, design)
    d["inspections"].append({
        "version": version, "at": _now(),
        "verdict": result.get("verdict"),
        "failed": result.get("failed", []),
        "unrun": result.get("unrun", []),
        "checks": {k: {kk: vv for kk, vv in v.items() if kk != "blocking"}
                   for k, v in result.get("checks", {}).items()},
    })
    save(led)


def inspection_for(design, version):
    """The gate. Returns the most recent inspection of that version, or None."""
    d = load()["designs"].get(design)
    if not d:
        return None
    got = [i for i in d.get("inspections", []) if i.get("version") == version]
    return got[-1] if got else None


# ---------------------------------------------------------------- visuals

def _b64(img, size=(420, 500)):
    im = img.copy()
    im.thumbnail(size, Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _on_grey(path, size=(420, 500)):
    if not os.path.exists(path):
        return None
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
    return _b64(Image.alpha_composite(bg, im), size)


def diff_heatmap(a_path, b_path, size=(420, 500)):
    """
    Where v2 differs from v1, in red over a faded v1.

    ⚠ The first version diffed ALPHA only, reasoning that "what moved is a
    change in where ink is". That hid the very first change it was asked to
    show: v2 answered a contrast failure by RECOLOURING the inks, and an
    alpha-only diff reported 0.0% changed on a file that plainly changed.

    So diff what a viewer actually sees — both versions composited onto the same
    ground, compared in RGB. That catches movement and recolour alike, which is
    what "see the change" has to mean.
    """
    if not (os.path.exists(a_path) and os.path.exists(b_path)):
        return None
    a = Image.open(a_path).convert("RGBA")
    b = Image.open(b_path).convert("RGBA")
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)

    ground = Image.new("RGBA", a.size, (255, 255, 255, 255))
    fa = Image.alpha_composite(ground, a).convert("RGB")
    fb = Image.alpha_composite(ground, b).convert("RGB")

    d = ImageChops.difference(fa, fb).convert("L")
    d = d.point(lambda v: 255 if v > 18 else 0)

    base = Image.new("RGBA", a.size, (245, 245, 245, 255))
    faded = Image.new("RGBA", a.size, (0, 0, 0, 0))
    faded.paste(a, (0, 0), a.getchannel("A").point(lambda v: int(v * 0.22)))
    base = Image.alpha_composite(base, faded)

    red = Image.new("RGBA", a.size, (214, 48, 49, 255))
    red.putalpha(d)
    changed = sum(d.histogram()[128:]) / float(a.width * a.height)
    return _b64(Image.alpha_composite(base, red), size), changed


# ---------------------------------------------------------------- report

CSS = """
:root{--bg:#fbfbfa;--panel:#fff;--line:#e4e2dd;--ink:#1f1d1a;--mut:#6b665e;
--ok:#2d7d46;--bad:#c0392b;--warn:#b7791f;--accent:#3a5a82}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.55 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--mut);margin:0 0 36px}
.design{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:26px;margin-bottom:28px}
.design h2{font-size:19px;margin:0 0 2px}
.design .id{color:var(--mut);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
font-size:12px;margin-bottom:20px}
.row{display:flex;gap:22px;flex-wrap:wrap;margin:18px 0}
.col{flex:1;min-width:230px}
.col h4{margin:0 0 8px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;
color:var(--mut);font-weight:600}
img{max-width:100%;border:1px solid var(--line);border-radius:6px;display:block}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:13px}
th{text-align:left;font-size:11px;letter-spacing:.07em;text-transform:uppercase;
color:var(--mut);border-bottom:1px solid var(--line);padding:7px 10px;font-weight:600}
td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
td.num{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
tr.fail td{background:#fdf0ee}
tr.fail td.num{color:var(--bad);font-weight:700}
tr.unrun td{background:#fdf7e8}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:11px;
font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.pill.pass{background:#e6f4ea;color:var(--ok)}
.pill.blocked{background:#fdeae7;color:var(--bad)}
.pill.unrun{background:#fdf3dd;color:var(--warn)}
.note{color:var(--mut);font-size:12px;padding-left:12px;border-left:2px solid var(--line)}
.changes{margin:10px 0 0;padding-left:18px}
.changes li{margin:4px 0}
.empty{color:var(--mut);font-style:italic;padding:14px 0}
.stamp{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
color:var(--mut)}
.gate{background:#f4f6f9;border-left:3px solid var(--accent);padding:12px 16px;
margin:16px 0;font-size:13px}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#161513;--panel:#1e1d1a;--line:#33312c;--ink:#eceae5;--mut:#a09a90}
tr.fail td{background:#2c1c1a}tr.unrun td{background:#2a2418}
.pill.pass{background:#1b3324}.pill.blocked{background:#33201d}
.pill.unrun{background:#2f2716}.gate{background:#1a1f26}}
"""


def build_report(led, out_dir):
    rows = []
    for design, d in sorted(led.get("designs", {}).items()):
        versions = d.get("versions", [])
        insps = d.get("inspections", [])
        name = design.replace("-", " ").title()

        body = [f'<div class="design"><h2>{name}</h2>'
                f'<div class="id">{design}</div>']

        if not versions:
            body.append('<div class="empty">No versions built yet.</div></div>')
            rows.append("".join(body))
            continue

        for v in versions:
            n = v["version"]
            body.append(f'<h4>Version {n} <span class="stamp">· {v["at"]}</span></h4>')
            if v.get("note"):
                body.append(f'<div class="note">{v["note"]}</div>')
            if v.get("changes"):
                body.append('<ul class="changes">'
                            + "".join(f"<li>{c}</li>" for c in v["changes"])
                            + "</ul>")

            imgs = []
            for label, key in (("On white", "onlight"), ("On black", "ondark"),
                               ("Detail 1:1", "detail")):
                p = v.get("files", {}).get(key)
                if p and os.path.exists(p):
                    imgs.append(f'<div class="col"><h4>{label}</h4>'
                                f'<img src="{_b64(Image.open(p).convert("RGB"))}"></div>')
            if n > 1:
                prev = next((x for x in versions if x["version"] == n - 1), None)
                if prev:
                    a = prev.get("files", {}).get("print")
                    b = v.get("files", {}).get("print")
                    if a and b:
                        hm = diff_heatmap(a, b)
                        if hm:
                            img, frac = hm
                            imgs.append(
                                f'<div class="col"><h4>Changed vs v{n-1} '
                                f'— {frac:.1%} of the canvas</h4>'
                                f'<img src="{img}"></div>')
            if imgs:
                body.append(f'<div class="row">{"".join(imgs)}</div>')

            insp = [i for i in insps if i["version"] == n]
            if insp:
                i = insp[-1]
                cls = {"pass": "pass", "blocked": "blocked"}.get(i["verdict"], "unrun")
                body.append(f'<p><span class="pill {cls}">{i["verdict"]}</span> '
                            f'<span class="stamp">inspected {i["at"]}</span></p>')
                body.append("<table><tr><th>Check</th><th>Measured</th>"
                            "<th>Required</th></tr>")
                for cname, c in i["checks"].items():
                    tcls = ("fail" if c.get("ok") is False else
                            "unrun" if c.get("ok") is None else "")
                    body.append(f'<tr class="{tcls}"><td>{cname}</td>'
                                f'<td class="num">{c.get("value","")}</td>'
                                f'<td class="num">{c.get("want","")}</td></tr>')
                    if c.get("note"):
                        body.append(f'<tr class="{tcls}"><td colspan="3" '
                                    f'class="note">{c["note"]}</td></tr>')
                body.append("</table>")
            else:
                body.append('<div class="gate">No inspection recorded for this '
                            'version. <strong>v' + str(n + 1) + ' is blocked</strong> '
                            'until one exists — that refusal is the point of the '
                            'gate, not an obstacle to it.</div>')

        body.append("</div>")
        rows.append("".join(body))

    total_v = sum(len(d.get("versions", [])) for d in led.get("designs", {}).values())
    total_i = sum(len(d.get("inspections", [])) for d in led.get("designs", {}).values())

    html = f"""<title>Mockup Change History</title>
<style>{CSS}</style>
<div class="wrap">
<h1>Mockup change history</h1>
<p class="sub">{len(led.get('designs',{}))} designs · {total_v} versions ·
{total_i} inspections · generated {_now()}</p>
<div class="gate"><strong>How to read this.</strong> Every version is appended,
never edited — so a v2 always sits below the v1 it answers, with the inspection
that forced it in between. Failed checks are red and carry the measured number,
because the number is what tells you what to change. The heatmap marks in red
exactly where v2 differs from v1, so a described change can be confirmed rather
than taken on trust.</div>
{"".join(rows) or '<div class="empty">Ledger is empty.</div>'}
</div>"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "history.html")
    open(path, "w").write(html)
    return path


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--show", help="print one design's ledger entries")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    a = ap.parse_args()

    led = load()
    if a.show:
        d = led["designs"].get(a.show)
        if not d:
            print(f"no entries for {a.show}")
            return
        print(json.dumps(d, indent=2))
        return

    path = build_report(led, a.out)
    print(f"wrote {path}")
    for design, d in sorted(led.get("designs", {}).items()):
        vs, ins = len(d.get("versions", [])), len(d.get("inspections", []))
        print(f"  {design:<22} {vs} version(s), {ins} inspection(s)")


if __name__ == "__main__":
    main()
