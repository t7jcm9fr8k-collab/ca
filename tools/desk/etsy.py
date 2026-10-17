"""Where every design in the Etsy pipeline (tools/etsy/) stands.

    import etsy
    etsy.collect(pathlib.Path("/path/to/repo"))   # -> dict, never raises

Reads only files already in the checkout. It never runs compose, qc, mockup
or listing generation, never writes, never touches the network. Python 3,
standard library only (no Pillow).

Nothing here is a remembered fact. A design's stage is worked out from:

    catalogue.json                 which designs exist, which are live
    recipes/*.json                 each layer's source plate and provenance
    compose.py                     the provenance/licence gate. Its own
                                   definitions are loaded from the file (see
                                   _load_defs), so this module cannot drift from
                                   what compose.py would refuse
    sources/                       which plates are on disk
    out/<id>-onlight.png           a full-size compose.py render
    out/history.json               the ledger: versions and QC inspections
    listing.py                     the listing validators, run on the catalogue
    out/calendar.md                schedule.py's output

Stage, in the order it is decided:

    listed              catalogue status is "live"
    proof-only          the recipe belongs to no catalogue design
    blocked-provenance  compose.py or schedule.py would refuse it today: the
                        recipe is missing, a layer's url/licence/traced is blank
                        or unusable, or a layer's plate is not in sources/
    qc-passed           the newest version's recorded inspection passed and the
                        inspected file is unchanged
    qc-blocked          ... or failed
    mocked-up           the ledger holds a version with no usable inspection
    composed            a full-size render is in out/ (a --draft one is not)
    sources-present     provenance cleared and every plate on disk, no render

Where a fact lives in a file git does not track (out/ is gitignored) the item
says "tracked": false. A fact that could not be read is null with a warning,
never zero: "no ledger" is not "no versions".
"""
import ast
import glob
import hashlib
import json
import os
import pathlib
import re
import struct
import subprocess
import datetime

ETSY = "tools/etsy"


# ---------------------------------------------------------------- reading

def _read_text(path, what, warnings):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, ValueError) as e:
        warnings.append(f"{what}: cannot read ({e.__class__.__name__}: {e})")
        return None


def _read_json(path, what, warnings):
    """(data, text), or (None, None) with a warning."""
    text = _read_text(path, what, warnings)
    if text is None:
        return None, None
    try:
        return json.loads(text), text
    except ValueError as e:
        warnings.append(f"{what}: not valid JSON ({e})")
        return None, None


def _line_of(text, needle, start=0):
    """1-based line number of the first line at or after index `start` (a
    line index) that contains needle, or None."""
    if text is None:
        return None
    for i, line in enumerate(text.split("\n")):
        if i >= start and needle in line:
            return i + 1
    return None


def _at(path, line=None):
    return f"{path}:{line}" if line else str(path)


def _git_tracked(root, warnings):
    """The set of tracked paths under tools/etsy, or None when git cannot say."""
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", ETSY],
                           capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        warnings.append(f"git ls-files: cannot run ({e.__class__.__name__}); "
                        f"'tracked' is null throughout")
        return None
    if r.returncode != 0:
        warnings.append("git ls-files failed (not a git checkout?); "
                        "'tracked' is null throughout")
        return None
    return {p for p in r.stdout.decode("utf-8", "replace").split("\0") if p}


def _load_defs(path, warnings):
    """
    The module-level assignments, functions and imports of a repo .py file,
    executed into a fresh namespace — without running the rest of it.

    compose.py imports Pillow at the top, but its provenance gate
    (check_provenance, licence_verdict and the allow-list they read) is plain
    Python. Loading only the definitions lets this module ask the real gate
    instead of keeping a copy that would drift. An import that fails (Pillow,
    sibling modules) is skipped; `if __name__ == "__main__"` is never run.
    """
    text = _read_text(path, str(path), warnings)
    if text is None:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        warnings.append(f"{path}: does not parse ({e})")
        return None
    ns = {"__file__": str(path), "__name__": "desk_gate_" + path.stem}
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign,
                                 ast.FunctionDef)):
            continue
        try:
            exec(compile(ast.Module([node], []), str(path), "exec"), ns)
        except Exception:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                warnings.append(f"{path}: line {node.lineno} could not be loaded")
    return ns


def _png_size(path):
    """(width, height) from the PNG header, or None."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def _image_size(path):
    """(width, height) of a PNG or JPEG from its header, or None."""
    png = _png_size(path)
    if png:
        return png
    try:
        with open(path, "rb") as f:
            data = f.read(1 << 20)
    except OSError:
        return None
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7 or marker == 0xFF:
            i += 1 if marker == 0xFF else 2
            continue
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def _sha256(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _plain_name(value):
    """names.safe_name's rule: a name that cannot be a path."""
    s = str(value)
    return bool(s) and s not in (".", "..") and s == os.path.basename(s) \
        and "\\" not in s and "\0" not in s and not os.path.isabs(s)


# ---------------------------------------------------------------- the ledger

def _load_ledger(etsy_dir, warnings):
    """(ledger, text, relpath). ledger is None when absent or unreadable."""
    rel = f"{ETSY}/out/history.json"
    path = etsy_dir / "out" / "history.json"
    if not path.exists():
        warnings.append(f"{rel} not found (out/ is untracked, so a fresh clone "
                        f"has none): versions and qc are null, not zero")
        return None, None, rel
    led, text = _read_json(path, rel, warnings)
    if led is None:
        return None, None, rel
    if not isinstance(led, dict) or not isinstance(led.get("designs"), dict):
        warnings.append(f"{rel}: has no 'designs' map; versions and qc are null")
        return None, None, rel
    return led, text, rel


def _inspection(etsy_dir, rec):
    """Is the file this inspection saw still the file on disk?  history.py
    inspection_status, read-only."""
    if not rec.get("checks"):
        return "unbound"
    if "file" not in rec:
        return "legacy"             # recorded before hashes were kept
    if not rec.get("file") or not rec.get("sha256"):
        return "unbound"
    p = pathlib.Path(rec["file"])
    p = p if p.is_absolute() else etsy_dir / p
    if not p.exists():
        return "missing"
    return "ok" if _sha256(p) == rec["sha256"] else "changed"


def _qc_and_versions(did, rid, etsy_dir, led, led_text, led_rel):
    """(versions, qc, latest_version, stale_note) for one design."""
    if led is None:
        return None, None, None, None
    entry = led["designs"].get(did) or led["designs"].get(rid)
    key = did if did in led["designs"] else rid
    if not isinstance(entry, dict):
        return 0, None, None, None
    versions = [v for v in entry.get("versions", []) if isinstance(v, dict)]
    insps = [i for i in entry.get("inspections", []) if isinstance(i, dict)]
    nums = [v.get("version") for v in versions + insps
            if isinstance(v.get("version"), int)]
    latest = max(nums) if nums else None
    mine = [i for i in insps if i.get("version") == latest]
    if not mine:
        return len(versions), None, latest, None
    rec = mine[-1]
    state = _inspection(etsy_dir, rec)
    qc = {
        "version": latest,
        "verdict": rec.get("verdict"),
        "failed": rec.get("failed", []),
        "unrun": rec.get("unrun", []),
        "at": rec.get("at"),
        "file": rec.get("file"),
        "file_state": state,
        "checks": {k: {"ok": c.get("ok"), "value": c.get("value"), "want": c.get("want")}
                   for k, c in (rec.get("checks") or {}).items() if isinstance(c, dict)},
        "tracked": False,
        "source": _at(led_rel, _line_of(led_text, f'"{key}": {{')),
    }
    return len(versions), qc, latest, state


def _failed_in_words(qc):
    out = []
    for name in qc["failed"][:4]:
        c = qc["checks"].get(name) or {}
        out.append(f"{name} {c.get('value')} (want {c.get('want')})")
    more = len(qc["failed"]) - 4
    return ", ".join(out) + (f" and {more} more" if more > 0 else "")


# ---------------------------------------------------------------- one design

def _layers(recipe, recipe_rel, recipe_text, sources_dir, sources_rel, gate,
            tracked_set, min_px):
    """The sources list for one recipe, in the recipe's order."""
    out = []
    cursor = 0
    for i, layer in enumerate(recipe.get("layers") or []):
        if not isinstance(layer, dict):
            continue
        name = layer.get("source", "")
        prov = layer.get("provenance") or {}
        lic = str(prov.get("licence", "")).strip() or None
        line = _line_of(recipe_text, f'"source": {json.dumps(name)}', cursor)
        lic_line = None
        if line:
            cursor = line
            lic_line = _line_of(recipe_text, '"licence"', line - 1)
        plain = _plain_name(name)
        f = sources_dir / name if plain else None
        rel = f"{sources_rel}/{name}"
        size = _image_size(f) if f and f.is_file() else None
        out.append({
            "file": name,
            "licence": lic,
            "licence_verdict": gate["licence_verdict"](lic) if gate and lic else None,
            "present": bool(f and f.is_file()),
            "size": list(size) if size else None,
            "soft": (min(size) < min_px) if size and min_px else None,
            "tracked": (rel in tracked_set) if tracked_set is not None else None,
            "wanted": layer.get("_wanted"),
            "url": str(prov.get("url", "")).strip() or None,
            "traced": str(prov.get("traced", "")).strip() or None,
            "layer": i,
            "plain_name": plain,
            "source": _at(recipe_rel, line),
            "licence_source": _at(recipe_rel, lic_line),
        })
    return out


def _blocked_on(recipe, sources, gate, sources_rel):
    """Why compose.py / schedule.py would refuse this recipe today, in words."""
    reasons = []
    if not recipe.get("layers"):
        reasons.append("the recipe has no layers")
    if gate is None:
        reasons.append("provenance could not be checked (compose.py unreadable)")
    else:
        problems = gate["check_provenance"](recipe)
        if problems:
            more = f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""
            reasons.append("provenance: " + "; ".join(problems[:3]) + more)
    for s in sources:
        what = s["wanted"] or f"layer {s['layer']}"
        if not s["plain_name"]:
            reasons.append(f"layer {s['layer']} source name {s['file']!r} is not a "
                           f"plain file name")
        elif not s["present"]:
            reasons.append(f"no source plate in {sources_rel}/ for {what} "
                           f"(expects {s['file']})")
    return "; ".join(reasons) or None


def _render_state(rid, out_dir, out_rel, canvas, tracked_set):
    """The compose.py render for this recipe id, or None when absent."""
    if not _plain_name(rid):
        return None
    files, sizes = [], []
    for way in ("onlight", "ondark"):
        p = out_dir / f"{rid}-{way}.png"
        if p.is_file():
            files.append(f"{out_rel}/{rid}-{way}.png")
            sizes.append(_png_size(p))
    if not files:
        return None
    full = (canvas is None or all(s == tuple(canvas) for s in sizes)) and len(files) == 2
    return {"files": files, "size": list(sizes[0]) if sizes[0] else None,
            "full_size": full, "draft": canvas is not None and not full,
            "tracked": (files[0] in tracked_set) if tracked_set is not None else None,
            "source": files[0]}


def _stage(entry, composed, versions, latest, qc, qc_state):
    """(stage, blocked_on) for a design that has a clear recipe and its plates."""
    if versions and latest is not None:
        if qc is None:
            return "mocked-up", f"v{latest} has no recorded QC inspection"
        if qc_state in ("ok", "legacy"):
            if qc["verdict"] == "pass":
                return "qc-passed", None
            if qc["verdict"] == "blocked":
                return "qc-blocked", f"QC v{latest} failed: {_failed_in_words(qc)}"
            return "mocked-up", (f"QC v{latest} verdict {qc['verdict']!r}; could not "
                                 f"run: {', '.join(qc['unrun']) or 'unknown'} "
                                 f"(unrun is not a pass)")
        return "mocked-up", (f"QC v{latest} record is not usable: its print file is "
                             f"{qc_state} since it was inspected")
    if composed and composed["full_size"]:
        return "composed", None
    note = None
    if composed and composed["draft"]:
        note = "only a --draft render is in out/ (not full size)"
    return "sources-present", note


# ---------------------------------------------------------------- listings

def _listings(catalogue, cat_rel, cat_text, lst, warnings):
    """Per-design listing check results and the roll-up."""
    designs = catalogue.get("designs") or []
    per = {}
    if lst is None or "report" not in lst:
        warnings.append(f"{ETSY}/listing.py unreadable: listing checks are null")
        return per, None
    errors = warns = 0
    for d in designs:
        try:
            issues = lst["report"](d, catalogue, quiet=True)
        except Exception as e:
            warnings.append(f"listing check of {d.get('id')} failed "
                            f"({e.__class__.__name__}: {e})")
            per[d.get("id")] = None
            continue
        e = [m for lvl, m in issues if lvl == "error"]
        w = [m for lvl, m in issues if lvl != "error"]
        errors += len(e)
        warns += len(w)
        per[d.get("id")] = {"errors": len(e), "warnings": len(w), "messages": e + w,
                            "source": _at(cat_rel, _line_of(cat_text, f'"id": "{d.get("id")}"'))}
    live = sum(1 for d in designs if d.get("status") == "live")
    return per, {"count": len(designs), "live": live, "errors": errors,
                 "warnings": warns, "source": cat_rel}


# ---------------------------------------------------------------- calendar

def _calendar(etsy_dir, tracked_set, warnings):
    out_dir = etsy_dir / "out"
    found = sorted(glob.glob(str(out_dir / "calendar*.md")))
    pref = out_dir / "calendar.md"        # the name schedule.py writes
    path = pref if pref.is_file() else (pathlib.Path(found[-1]) if found else None)
    if path is None:
        warnings.append(f"{ETSY}/out/calendar.md not found (schedule.py writes it; "
                        f"out/ is untracked): calendar is null")
        return None
    rel = f"{ETSY}/out/{path.name}"
    text = _read_text(path, rel, warnings)
    if text is None:
        return None
    dates = re.findall(r"^\*\*(\d{4}-\d{2}-\d{2}) ", text, re.M)
    releases = re.findall(r"^\| (\d{4}-\d{2}-\d{2}|\*\*no slot left\*\*) \| .* \| .* \|$",
                          text, re.M)
    blocked = len(re.findall(r"^\|.*\*\*BLOCKED", text, re.M))
    try:
        mtime = datetime.datetime.fromtimestamp(
            path.stat().st_mtime, datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    except OSError:
        mtime = None
    return {"file": rel, "slots": len(dates),
            "first": min(dates) if dates else None, "last": max(dates) if dates else None,
            "releases": len(releases), "releases_blocked": blocked,
            "modified": mtime,
            "tracked": (rel in tracked_set) if tracked_set is not None else None,
            "source": rel}


# ---------------------------------------------------------------- collect

def collect(repo_root):
    warnings = []
    try:
        return _collect(pathlib.Path(repo_root), warnings)
    except Exception as e:      # the desk page must still draw
        warnings.append(f"etsy collector failed ({e.__class__.__name__}: {e})")
        return {"designs": [], "listings": None, "calendar": None,
                "sources_dir": {"files": None, "source": f"{ETSY}/sources"},
                "warnings": warnings}


def _collect(root, warnings):
    etsy_dir = root / ETSY
    sources_rel, out_rel = f"{ETSY}/sources", f"{ETSY}/out"
    tracked_set = _git_tracked(root, warnings)

    def tracked(rel):
        return (rel in tracked_set) if tracked_set is not None else None

    gate_ns = _load_defs(etsy_dir / "compose.py", warnings)
    gate = gate_ns if gate_ns and "check_provenance" in gate_ns \
        and "licence_verdict" in gate_ns else None
    canvas = gate_ns.get("CANVAS") if gate_ns else None
    lst = _load_defs(etsy_dir / "listing.py", warnings)

    cat_rel = f"{ETSY}/catalogue.json"
    catalogue, cat_text = _read_json(etsy_dir / "catalogue.json", cat_rel, warnings)
    cat_designs = (catalogue or {}).get("designs") or []

    led, led_text, led_rel = _load_ledger(etsy_dir, warnings)

    sources_dir = etsy_dir / "sources"
    out_dir = etsy_dir / "out"

    # every recipe on disk, by path
    recipe_files = sorted(glob.glob(str(etsy_dir / "recipes" / "*.json")))
    claimed = set()
    todo = []       # (catalogue design or None, recipe path or None)
    for d in cat_designs:
        did = d.get("id", "")
        rpath = None
        if d.get("recipe"):
            rpath = (etsy_dir / d["recipe"])
        elif _plain_name(did) and (etsy_dir / "recipes" / f"{did}.json").exists():
            rpath = etsy_dir / "recipes" / f"{did}.json"
        if rpath is not None:
            claimed.add(str(rpath.resolve()))
        todo.append((d, rpath))
    for f in recipe_files:
        if str(pathlib.Path(f).resolve()) not in claimed:
            todo.append((None, pathlib.Path(f)))

    designs = []
    used_sources = set()
    for cat, rpath in todo:
        item = _design(cat, rpath, root, etsy_dir, sources_dir, sources_rel, out_dir,
                       out_rel, gate, canvas, tracked_set, led, led_text, led_rel,
                       cat_rel, cat_text, warnings)
        used_sources.update(s["file"] for s in item["sources"])
        designs.append(item)

    per, listings = (_listings(catalogue, cat_rel, cat_text, lst, warnings)
                     if catalogue is not None else ({}, None))
    for item in designs:
        if item["id"] in per:
            item["listing"] = per[item["id"]]

    files = None
    if sources_dir.is_dir():
        files = sorted(p.name for p in sources_dir.iterdir() if p.is_file())
    else:
        warnings.append(f"{sources_rel}/ not found: no source plates on disk")
    sd = {"files": files, "source": sources_rel}
    if files is not None:
        sd["untracked"] = ([n for n in files if not tracked(f"{sources_rel}/{n}")]
                           if tracked_set is not None else None)
        sd["unreferenced"] = [n for n in files if n not in used_sources]
        sd["missing"] = sorted(n for n in used_sources if n not in files)

    return {"designs": designs, "listings": listings,
            "calendar": _calendar(etsy_dir, tracked_set, warnings),
            "sources_dir": sd,
            "ledger": {"file": led_rel, "present": led is not None,
                       "tracked": tracked(led_rel), "source": led_rel},
            "warnings": warnings}


def _design(cat, rpath, root, etsy_dir, sources_dir, sources_rel, out_dir, out_rel,
            gate, canvas, tracked_set, led, led_text, led_rel, cat_rel, cat_text,
            warnings):
    recipe = recipe_text = None
    recipe_rel = None
    if rpath is not None:
        recipe_rel = rpath.relative_to(root).as_posix() if rpath.is_relative_to(root) \
            else str(rpath)
        if rpath.exists():
            recipe, recipe_text = _read_json(rpath, recipe_rel, warnings)
        else:
            warnings.append(f"{recipe_rel}: recipe named by "
                            f"{'the catalogue' if cat else 'the recipes folder'} "
                            f"does not exist")
    did = (cat or {}).get("id") or (recipe or {}).get("id") or \
        (rpath.stem if rpath else "?")
    rid = (recipe or {}).get("id") or did
    cat_line = _line_of(cat_text, f'"id": "{did}"') if cat else None
    item = {
        "id": did,
        "title": (cat or {}).get("name") or (recipe or {}).get("title") or did,
        "etsy_title": (cat or {}).get("title"),
        "catalogue_status": (cat or {}).get("status"),
        "recipe": recipe_rel,
        "stage": None, "blocked_on": None, "sources": [], "qc": None,
        "versions": None, "render": None, "listing": None, "notes": [],
        "source": _at(cat_rel, cat_line) if cat else recipe_rel,
    }

    live = bool(cat) and cat.get("status") == "live"
    if recipe is not None:
        item["sources"] = _layers(recipe, recipe_rel, recipe_text, sources_dir,
                                  sources_rel, gate, tracked_set,
                                  gate.get("MIN_SOURCE_PX") if gate else None)
    versions, qc, latest, qc_state = _qc_and_versions(
        did, rid, etsy_dir, led, led_text, led_rel)
    item["versions"], item["qc"] = versions, qc
    item["render"] = _render_state(rid, out_dir, out_rel, canvas, tracked_set)

    if live:
        item["stage"] = "listed"
        if cat.get("listing_id"):
            item["listing_id"] = cat["listing_id"]
        return item

    if recipe is None:
        item["stage"] = "blocked-provenance"
        item["blocked_on"] = (f"recipe {recipe_rel} is missing or unreadable"
                              if recipe_rel else "no recipe for this design")
        return item

    item["notes"] = [
        f"{s['file']} is {s['size'][0]}x{s['size'][1]}, under the {gate['MIN_SOURCE_PX']}px "
        f"short-edge floor: compose.py warns that it goes soft at chest size"
        for s in item["sources"] if s["soft"]]
    blocked = _blocked_on(recipe, item["sources"], gate, sources_rel)
    if cat is None:
        item["stage"] = "proof-only"
        item["blocked_on"] = blocked
        item["notes"].append("recipe belongs to no design in catalogue.json: "
                             "a pipeline proof")
        return item
    if blocked:
        item["stage"], item["blocked_on"] = "blocked-provenance", blocked
        return item
    item["stage"], item["blocked_on"] = _stage(
        item, item["render"], versions, latest, qc, qc_state)
    return item


if __name__ == "__main__":
    import sys
    root = pathlib.Path(__file__).resolve().parent.parent.parent
    json.dump(collect(root), sys.stdout, indent=1)
    print()
