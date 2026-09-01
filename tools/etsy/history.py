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

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;600&'
         'family=Source+Sans+3:wght@400;600&display=swap">')

# A proof sheet, not a report. The palette is lifted from the recipe inks the
# pipeline actually prints with, the mono face carries every measured value
# because on a press check the numbers are the content, and Archivo echoes the
# Archivo Black that goes on the shirts.
CSS = """
:root{
  --paper:#faf8f4; --plate:#fffefb; --rule:#e3ded2; --ink:#16150f;
  --muted:#6e685c; --amber:#b8701c; --pass:#2f6e45; --block:#a83232;
  --watch:#8a6a12; --wash:#f3efe6;
  --display:'Archivo',system-ui,sans-serif;
  --body:'Source Sans 3',system-ui,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#131210; --plate:#1b1a16; --rule:#33302a; --ink:#efece4;
  --muted:#9a9384; --amber:#e0a24e; --pass:#63b183; --block:#e08078;
  --watch:#d4ab4a; --wash:#211f1a;
}}
:root[data-theme="dark"]{
  --paper:#131210; --plate:#1b1a16; --rule:#33302a; --ink:#efece4;
  --muted:#9a9384; --amber:#e0a24e; --pass:#63b183; --block:#e08078;
  --watch:#d4ab4a; --wash:#211f1a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font:16px/1.6 var(--body);-webkit-font-smoothing:antialiased}
.sheet{max-width:1120px;margin:0 auto;padding:56px 28px 96px}

.masthead{border-bottom:2px solid var(--ink);padding-bottom:18px;margin-bottom:8px}
h1{font:600 30px/1.15 var(--display);margin:0;letter-spacing:-.015em;
  text-wrap:balance}
.meta{display:flex;flex-wrap:wrap;gap:22px;margin:12px 0 40px;
  font:400 12px/1 var(--mono);color:var(--muted);font-variant-numeric:tabular-nums}
.legend{background:var(--wash);border-left:3px solid var(--amber);
  padding:16px 20px;margin:0 0 40px;font-size:14.5px;max-width:66ch}
.legend strong{font-family:var(--display);font-weight:600}

.plate{background:var(--plate);border:1px solid var(--rule);border-radius:3px;
  padding:30px;margin-bottom:26px;position:relative}
/* registration marks — the one flourish, and it belongs to the subject */
.plate::before,.plate::after{content:"";position:absolute;width:11px;height:11px;
  border:1px solid var(--rule)}
.plate::before{top:9px;left:9px;border-right:0;border-bottom:0}
.plate::after{bottom:9px;right:9px;border-left:0;border-top:0}
.plate h2{font:600 21px/1.2 var(--display);margin:0 0 2px;letter-spacing:-.01em}
.slug{font:400 11.5px/1 var(--mono);color:var(--muted);margin-bottom:26px;
  letter-spacing:.04em}

.ver{border-top:1px solid var(--rule);padding-top:22px;margin-top:26px}
.ver:first-of-type{border-top:0;padding-top:0;margin-top:0}
.vhead{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:6px}
.vhead h3{font:600 13px/1 var(--display);margin:0;letter-spacing:.1em;
  text-transform:uppercase}
.stamp{font:400 11.5px/1 var(--mono);color:var(--muted);
  font-variant-numeric:tabular-nums}
.why{color:var(--muted);font-size:14.5px;margin:6px 0 0;max-width:66ch}
.changes{margin:12px 0 0;padding:0;list-style:none;max-width:70ch}
.changes li{position:relative;padding-left:20px;margin:7px 0;font-size:14.5px}
.changes li::before{content:"";position:absolute;left:2px;top:.62em;width:9px;
  height:1px;background:var(--amber)}

.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
  gap:20px;margin:22px 0 6px}
.shot h4{margin:0 0 8px;font:600 10.5px/1 var(--mono);letter-spacing:.11em;
  text-transform:uppercase;color:var(--muted)}
img{width:100%;border:1px solid var(--rule);border-radius:2px;display:block}

.verdict{display:inline-flex;align-items:center;gap:8px;
  font:600 10.5px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;
  padding:6px 11px;border-radius:2px;margin:20px 0 0}
.verdict.pass{color:var(--pass);background:color-mix(in srgb,var(--pass) 12%,transparent)}
.verdict.blocked{color:var(--block);background:color-mix(in srgb,var(--block) 12%,transparent)}
.verdict.unrun{color:var(--watch);background:color-mix(in srgb,var(--watch) 14%,transparent)}

.checks{width:100%;border-collapse:collapse;margin:14px 0 0;
  font-variant-numeric:tabular-nums}
.checks th{text-align:left;font:600 10px/1 var(--mono);letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);padding:0 12px 9px;
  border-bottom:1px solid var(--ink)}
.checks th.n,.checks td.n{text-align:right}
.checks td{padding:9px 12px;border-bottom:1px solid var(--rule);font-size:14px;
  vertical-align:baseline}
.checks td.n{font:400 12.5px/1.5 var(--mono)}
.checks tr.f td{background:color-mix(in srgb,var(--block) 7%,transparent)}
.checks tr.f td.n{color:var(--block);font-weight:600}
.checks tr.u td{background:color-mix(in srgb,var(--watch) 8%,transparent)}
.checks td.tag{font:400 11px/1 var(--mono);color:var(--muted);letter-spacing:.05em}
.remark{color:var(--muted);font-size:13px;padding:2px 12px 11px 12px!important;
  border-bottom:1px solid var(--rule)!important;max-width:0}

.gate{background:var(--wash);border-left:3px solid var(--block);padding:14px 18px;
  margin:20px 0 0;font-size:14px;max-width:70ch}
.gate strong{font-family:var(--display);font-weight:600}
.none{color:var(--muted);font-style:italic;padding:16px 0}
@media (max-width:640px){.sheet{padding:34px 18px 64px}h1{font-size:24px}}
"""
def build_report(led, out_dir):
    plates = []
    for design, d in sorted(led.get("designs", {}).items()):
        versions = d.get("versions", [])
        insps = d.get("inspections", [])
        name = design.replace("-", " ").title()

        p = [f'<section class="plate"><h2>{name}</h2>'
             f'<div class="slug">{design}</div>']

        if not versions:
            p.append('<p class="none">No versions built yet.</p></section>')
            plates.append("".join(p))
            continue

        for v in versions:
            n = v["version"]
            p.append('<div class="ver">')
            p.append(f'<div class="vhead"><h3>Version {n}</h3>'
                     f'<span class="stamp">{v["at"]}</span></div>')
            if v.get("note"):
                p.append(f'<p class="why">{v["note"]}</p>')
            if v.get("changes"):
                p.append('<ul class="changes">'
                         + "".join(f"<li>{c}</li>" for c in v["changes"])
                         + "</ul>")

            shots = []
            for label, key in (("On white", "white"), ("On black", "black"),
                               ("Detail · 1:1", "detail")):
                fp = v.get("files", {}).get(key)
                if fp and os.path.exists(fp):
                    shots.append(f'<figure class="shot"><h4>{label}</h4>'
                                 f'<img alt="{name} v{n} {label}" '
                                 f'src="{_b64(Image.open(fp).convert("RGB"))}">'
                                 f'</figure>')
            if n > 1:
                prev = next((x for x in versions if x["version"] == n - 1), None)
                if prev:
                    a = prev.get("files", {}).get("print")
                    b = v.get("files", {}).get("print")
                    if a and b:
                        hm = diff_heatmap(a, b)
                        if hm:
                            im, frac = hm
                            shots.append(
                                f'<figure class="shot"><h4>Changed vs v{n-1} · '
                                f'{frac:.1%}</h4><img alt="difference from '
                                f'version {n-1}" src="{im}"></figure>')
            if shots:
                p.append(f'<div class="shots">{"".join(shots)}</div>')

            mine = [i for i in insps if i["version"] == n]
            if mine:
                i = mine[-1]
                cls = {"pass": "pass", "blocked": "blocked"}.get(
                    i["verdict"], "unrun")
                p.append(f'<div class="verdict {cls}">{i["verdict"]}</div>'
                         f' <span class="stamp">inspected {i["at"]}</span>')
                p.append('<table class="checks"><thead><tr><th>Check</th>'
                         '<th class="n">Measured</th><th class="n">Required</th>'
                         '<th></th></tr></thead><tbody>')
                for cname, c in i["checks"].items():
                    rc = ("f" if c.get("ok") is False else
                          "u" if c.get("ok") is None else "")
                    tag = "reported" if c.get("reported_only") else ""
                    p.append(f'<tr class="{rc}"><td>{cname}</td>'
                             f'<td class="n">{c.get("value","")}</td>'
                             f'<td class="n">{c.get("want","")}</td>'
                             f'<td class="tag">{tag}</td></tr>')
                    if c.get("note"):
                        p.append(f'<tr class="{rc}"><td colspan="4" '
                                 f'class="remark">{c["note"]}</td></tr>')
                p.append("</tbody></table>")
            else:
                p.append(f'<div class="gate">No inspection recorded. '
                         f'<strong>Version {n + 1} is blocked</strong> until one '
                         f'exists — that refusal is the gate working, not an '
                         f'obstacle to it.</div>')
            p.append("</div>")

        p.append("</section>")
        plates.append("".join(p))

    designs = led.get("designs", {})
    nv = sum(len(d.get("versions", [])) for d in designs.values())
    ni = sum(len(d.get("inspections", [])) for d in designs.values())

    html = f"""<title>Press Check Ledger</title>
{FONTS}
<style>{CSS}</style>
<div class="sheet">
  <header class="masthead"><h1>Press check ledger</h1></header>
  <div class="meta"><span>{len(designs)} designs</span>
    <span>{nv} versions</span><span>{ni} inspections</span>
    <span>{_now()}</span></div>

  <p class="legend"><strong>How to read this.</strong> Every version is appended,
  never edited — so a v2 always sits below the v1 it answers, with the inspection
  that forced it in between. Failed checks carry the measured number, because the
  number is what tells you what to change. Checks marked <em>reported</em> are
  measured but never block. The difference panel marks in red exactly where a
  version diverges from the one before it, so a described change can be confirmed
  rather than taken on trust.</p>

  {"".join(plates) or '<p class="none">Ledger is empty.</p>'}
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
