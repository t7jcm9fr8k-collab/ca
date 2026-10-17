"""The desk: one page that says where every part of the work stands.

Reads only what is already in the repository (no network, no backtests,
no broker), so it can run in a cloud session or on the Mac alike:

    python3 tools/desk/desk.py                 # writes tools/desk/out/desk.{json,html}
    python3 tools/desk/desk.py --out DIR       # somewhere else
    python3 tools/desk/desk.py --json          # print the JSON, write nothing

Every fact in desk.json carries the file (and usually the line) it was
read from. The page is template.html with that JSON embedded, so it opens
from disk with no server.
"""
import argparse
import datetime
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import etsy    # noqa: E402
import market  # noqa: E402


def load_actions(root):
    path = root / "tools" / "desk" / "actions.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        return {"actions": [], "warnings": [f"actions.json unreadable: {e}"]}
    data.setdefault("warnings", [])
    data["warnings"] += check_actions(root, data.get("actions", []))
    return data


def check_actions(root, actions):
    """actions.json was written by hand from the docs; prove each quoted
    command still appears verbatim in the file it cites, so a drifted or
    invented command shows up as a warning instead of a copy button."""
    warnings = []
    for a in actions:
        path, _, line = str(a.get("source", "")).partition(":")
        try:
            text = (root / path).read_text()
        except (OSError, ValueError):
            warnings.append(f"{a.get('id')}: cited source {path!r} is unreadable")
            continue
        lines = text.splitlines()
        near = None
        if line.isdigit():  # the commands must sit near the cited line, not just anywhere;
            n = int(line)   # a block of k commands may run k lines on from where it starts
            k = len(a.get("commands", []))
            near = "\n".join(lines[max(n - 1 - CITE_WINDOW, 0):n + CITE_WINDOW + k])
        for cmd in a.get("commands", []):
            cmd = cmd.strip()
            if not cmd:
                continue
            if cmd not in text:
                warnings.append(f"{a.get('id')}: command not found verbatim in {path}: {cmd[:80]}")
            elif near is not None and cmd not in near:
                warnings.append(f"{a.get('id')}: command is in {path} but not within "
                                f"{CITE_WINDOW} lines of :{line}: {cmd[:80]}")
    return warnings


CITE_WINDOW = 5


def collect(root=ROOT):
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%MZ"),
        "market": market.collect(root),
        "etsy": etsy.collect(root),
        "actions": load_actions(root),
    }


def render(desk, standalone=True):
    """The page with desk embedded. standalone=False gives the bare fragment
    the artifact publisher wraps in its own <html>; True opens from disk."""
    page = (HERE / "template.html").read_text()
    blob = json.dumps(desk, indent=1).replace("</", "<\\/")
    if "/*DESK*/null" not in page:
        raise SystemExit("template.html lost its /*DESK*/null placeholder")
    page = page.replace("/*DESK*/null", blob, 1)
    if standalone:
        page = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                + page + "\n</html>\n")
    return page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "out")
    ap.add_argument("--json", action="store_true", help="print the JSON and exit")
    args = ap.parse_args(argv)

    desk = collect()
    if args.json:
        print(json.dumps(desk, indent=1))
        return 0
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "desk.json").write_text(json.dumps(desk, indent=1) + "\n")
    (args.out / "desk.html").write_text(render(desk))
    (args.out / "desk-fragment.html").write_text(render(desk, standalone=False))
    warnings = (desk["market"].get("warnings", []) + desk["etsy"].get("warnings", [])
                + desk["actions"].get("warnings", []))
    print(f"wrote {args.out / 'desk.html'}  ({len(warnings)} warnings)")
    for w in warnings:
        print(f"  warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
