#!/usr/bin/env python3
"""
market.py — read-only state of the market-research pipeline in tools/market/.

    collect(repo_root) -> dict

Reads files already in the repo and reports what they say: the trial count, the
pre-registered tests and their verdicts, the grade of each idea, the bar files,
the saved runs, the strategies, and the commit the repo is at. It imports
nothing from tools/market, runs no backtest, touches no broker, uses no network
and writes nothing. Standard library only.

Every number comes from a file at runtime. Every item carries `source`, the
repo-relative "path:line" where the fact was read. Two kinds of item have no
single line and say so: a run file's size comes from the filesystem (source is
the path), and the commit comes from `git log` (source is "git log -1").

A file that is missing or does not parse does not raise. The field stays in the
output with value None, and a string naming the file and the problem is added to
`warnings`. A test whose heading is found but whose verdict sentence is not
keeps verdict None and warns.

Quotes from EVIDENCE.md are taken from the text with its ** and ` markup
removed and its line breaks and runs of spaces collapsed to one space, and are
cut at 200 characters.
"""
import ast
import bisect
import json
import pathlib
import re
import subprocess

MARKET = "tools/market"
EVIDENCE = MARKET + "/EVIDENCE.md"
TRIALS = MARKET + "/trials.json"
STRATEGIES = MARKET + "/strategies.py"
BARS = MARKET + "/bars"
RUNS = MARKET + "/runs"

QUOTE_MAX = 200

# Where each test lives in EVIDENCE.md and how to find its verdict and headline.
# The patterns locate sentences; the words and numbers come from the file.
TESTS = [
    {"name": "E-15 replication",
     "heading": r"^E-15 · The replication",
     "verdict": r"REPLICATES: [^.]*?positive mean",
     "verdict_last": True,          # the eight-file run is superseded by the nine-file run below it
     "headline": r"Every mean is positive and every t_ep is above 2 \([^)]*\)\."},
    {"name": "Trial 3 official close",
     "heading": r"^Trial 3 — the official close",
     "verdict": r"Method #1 stays where trials 1 and 2 put it: .*?Do not trade it\.",
     "headline": r"gross \S+ ± \S+ bp/session \([^)]*\); the published effect .*? is EXCLUDED by this sample"},
    {"name": "Cross-section",
     "heading": r"^The cross-section — ",
     "verdict": r"VERDICT: NULL — \d+ of \d+ conditions",
     "headline": r"Both are null by the rule that was fixed before the data was touched\."},
    {"name": "Month-end overlay",
     "heading": r"^The month-end overlay — ",
     "verdict": r"VERDICT PARTIAL — DO NOT TRADE \([^)]*\)",
     "headline": r"PARTIAL by the rule written before the data was touched\. [^.]*\."},
]

GRADES_SECTION = r"^Each one, in a few lines"
GRADE_HEADING = re.compile(r"^(\d+) · (.+?) — (.+)$")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


# ---------------------------------------------------------------- helpers

def _read_lines(root, rel, warnings):
    """The file's lines, or None with a warning."""
    try:
        return (root / rel).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        warnings.append(f"{rel}: cannot read ({e.__class__.__name__}: {e})")
        return None


def _git(root, args):
    """stdout of a git command run in root, or raises RuntimeError."""
    try:
        p = subprocess.run(["git", "-C", str(root)] + args, capture_output=True,
                           text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"git {' '.join(args)}: {e}")
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip() or 'exit ' + str(p.returncode)}")
    return p.stdout


def _trim(text):
    if len(text) <= QUOTE_MAX:
        return text
    return text[:QUOTE_MAX - 3].rstrip() + "..."


def _headings(lines):
    """[(lineno, level, text)] for ATX headings outside code fences. lineno is 1-based."""
    out = []
    fenced = False
    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            fenced = not fenced
            continue
        m = None if fenced else re.match(r"^(#{1,6}) +(.*?)\s*$", line)
        if m:
            out.append((i, len(m.group(1)), m.group(2)))
    return out


def _section_end(headings, k, n_lines):
    """Last line (1-based) of heading k's section: up to the next heading of the same or higher level."""
    _, level, _ = headings[k]
    for lineno, lvl, _ in headings[k + 1:]:
        if lvl <= level:
            return lineno - 1
    return n_lines


def _find_heading(headings, pattern):
    for k, (_, _, text) in enumerate(headings):
        if re.search(pattern, text):
            return k
    return None


def _paragraphs(lines, first, last):
    """Blank-line separated paragraphs of lines[first..last] (1-based), as (text, starts, linenos).

    text is the paragraph on one line with markup removed; starts[j] is the offset in text
    where source line linenos[j] begins, so a match can be traced back to its line.
    """
    paras, cur = [], []
    for n in range(first, last + 1):
        if lines[n - 1].strip():
            cur.append(n)
        elif cur:
            paras.append(cur)
            cur = []
    if cur:
        paras.append(cur)
    out = []
    for nums in paras:
        text, starts = "", []
        for n in nums:
            piece = re.sub(r"^\s*>\s?", "", lines[n - 1])
            piece = re.sub(r"\*\*|`", "", piece)
            piece = re.sub(r"\s+", " ", piece).strip()
            starts.append(len(text))
            text += piece + " "
        out.append((text, starts, nums))
    return out


def _quote(lines, first, last, pattern, take_last=False):
    """(quote, lineno) of the first (or last) match of pattern in lines[first..last], else (None, None)."""
    rx = re.compile(pattern)
    found = (None, None)
    for text, starts, nums in _paragraphs(lines, first, last):
        m = rx.search(text)
        if m:
            found = (_trim(m.group(0)), nums[bisect.bisect_right(starts, m.start()) - 1])
            if not take_last:
                break
    return found


# ---------------------------------------------------------------- trials

def _trials(root, warnings):
    out = {"total": None, "entries": None, "open_questions": None, "source": TRIALS}
    lines = _read_lines(root, TRIALS, warnings)
    if lines is None:
        return out
    try:
        doc = json.loads("\n".join(lines))
        entries = doc["entries"]
        # the line each entry starts on: the n-th "as_of" key in the file
        starts = [i for i, ln in enumerate(lines, 1) if re.match(r'\s*"as_of"\s*:', ln)]
        rows = []
        for k, e in enumerate(entries):
            line = starts[k] if k < len(starts) else 1
            rows.append({"as_of": e["as_of"], "count": int(e["count"]),
                         "in_ledger": bool(e["in_ledger"]), "what": e["what"],
                         "status": e.get("status"), "cited": e.get("source"),
                         "source": f"{TRIALS}:{line}"})
        questions = doc.get("open_questions_for_the_owner", [])
    except (ValueError, KeyError, TypeError) as e:
        warnings.append(f"{TRIALS}: unexpected content ({e.__class__.__name__}: {e})")
        return out
    out["entries"] = rows
    out["total"] = sum(r["count"] for r in rows)
    out["open_questions"] = list(questions)
    return out


# ---------------------------------------------------------------- tests and grades

def _tests(lines, warnings):
    if lines is None:
        return None
    heads = _headings(lines)
    out = []
    for spec in TESTS:
        k = _find_heading(heads, spec["heading"])
        row = {"name": spec["name"], "date": None, "verdict": None, "headline": None,
               "heading": None, "source": EVIDENCE}
        out.append(row)
        if k is None:
            warnings.append(f"{EVIDENCE}: no heading matching /{spec['heading']}/ for test '{spec['name']}'")
            continue
        h_line, _, h_text = heads[k]
        last = _section_end(heads, k, len(lines))
        row["heading"] = h_text
        row["source"] = f"{EVIDENCE}:{h_line}"
        m = DATE.search(h_text) or DATE.search("\n".join(lines[h_line:last]))
        row["date"] = m.group(0) if m else None
        if row["date"] is None:
            warnings.append(f"{EVIDENCE}:{h_line}: no date in section '{spec['name']}'")
        for field in ("verdict", "headline"):
            quote, line = _quote(lines, h_line + 1, last, spec[field],
                                 take_last=field == "verdict" and spec.get("verdict_last", False))
            if quote is None:
                warnings.append(f"{EVIDENCE}:{h_line}: no {field} sentence for '{spec['name']}' "
                                f"(/{spec[field]}/)")
                continue
            row[field] = quote
            if field == "verdict":
                row["source"] = f"{EVIDENCE}:{line}"
            else:
                row["headline_source"] = f"{EVIDENCE}:{line}"
    return out


def _grades(lines, warnings):
    if lines is None:
        return None
    heads = _headings(lines)
    k = _find_heading(heads, GRADES_SECTION)
    if k is None:
        warnings.append(f"{EVIDENCE}: no '## Each one, in a few lines' section")
        return None
    last = _section_end(heads, k, len(lines))
    out = []
    for lineno, level, text in heads[k + 1:]:
        if lineno > last:
            break
        m = GRADE_HEADING.match(text) if level == 3 else None
        if m:
            out.append({"rank": int(m.group(1)), "idea": m.group(2), "grade": m.group(3),
                        "source": f"{EVIDENCE}:{lineno}"})
        else:
            warnings.append(f"{EVIDENCE}:{lineno}: heading '{text}' is not 'N · Title — grade'")
    return out


# ---------------------------------------------------------------- bars, runs, strategies

def _bar_file(root, rel, warnings):
    """rows and first/last date of one bar CSV. Comment lines and the header are skipped."""
    lines = _read_lines(root, rel, warnings)
    if lines is None:
        return None
    first = last = None
    rows = 0
    for n, line in enumerate(lines, 1):
        if line.startswith("#") or not DATE.match(line):
            continue                            # comment, header or blank
        rows += 1
        if first is None:
            first = (line.split(",")[0], n)
        last = (line.split(",")[0], n)
    if rows == 0:
        warnings.append(f"{rel}: no data rows")
        return {"file": rel.rsplit("/", 1)[-1], "rows": 0, "first_date": None,
                "last_date": None, "source": rel}
    return {"file": rel.rsplit("/", 1)[-1], "rows": rows, "first_date": first[0],
            "last_date": last[0], "source": f"{rel}:{first[1]}", "last_source": f"{rel}:{last[1]}"}


def _bars(root, warnings):
    try:
        tracked = _git(root, ["ls-files", BARS]).splitlines()
    except RuntimeError as e:
        warnings.append(f"{BARS}: cannot list tracked files ({e})")
        return None
    out = []
    for rel in sorted(p for p in tracked if p.endswith(".csv")):
        row = _bar_file(root, rel, warnings)
        if row:
            out.append(row)
    if not out:
        warnings.append(f"{BARS}: no tracked CSV files")
    return out


def _runs(root, warnings):
    base = root / RUNS
    if not base.is_dir():
        warnings.append(f"{RUNS}: not a directory")
        return None
    out = []
    for p in sorted(base.iterdir()):
        if p.name.startswith("."):
            continue
        # one level of recursion: files directly in runs/, and files directly in its subdirectories
        for f in sorted(p.iterdir()) if p.is_dir() else [p]:
            if f.is_file() and not f.name.startswith("."):
                rel = f.relative_to(base).as_posix()
                out.append({"file": rel, "bytes": f.stat().st_size, "source": f"{RUNS}/{rel}"})
    return out


def _strategies(root, warnings):
    lines = _read_lines(root, STRATEGIES, warnings)
    if lines is None:
        return None, None
    try:
        tree = ast.parse("\n".join(lines))
    except SyntaxError as e:
        warnings.append(f"{STRATEGIES}: does not parse ({e})")
        return None, None
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [getattr(node, "target", None)]
        if any(isinstance(t, ast.Name) and t.id == "REGISTRY" for t in targets) \
                and isinstance(getattr(node, "value", None), ast.Dict):
            keys = [k.value for k in node.value.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            return keys, f"{STRATEGIES}:{node.lineno}"
    warnings.append(f"{STRATEGIES}: no REGISTRY dict found")
    return None, None


def _head(root, warnings):
    try:
        sha, date, subject = _git(root, ["log", "-1", "--format=%h%x00%ad%x00%s", "--date=short"]).strip().split("\0")
    except (RuntimeError, ValueError) as e:
        warnings.append(f"git log -1: {e}")
        return None
    return {"commit": sha, "date": date, "subject": subject, "source": "git log -1"}


# ---------------------------------------------------------------- entry point

def collect(repo_root):
    """The state of the market-research pipeline as a dict. Never raises on a missing file."""
    root = pathlib.Path(repo_root)
    warnings = []
    evidence = _read_lines(root, EVIDENCE, warnings)
    strategies, strategies_source = _strategies(root, warnings)
    return {
        "trials": _trials(root, warnings),
        "tests": _tests(evidence, warnings),
        "grades": _grades(evidence, warnings),
        "bars": _bars(root, warnings),
        "runs": _runs(root, warnings),
        "strategies": strategies,
        "strategies_source": strategies_source,
        "head": _head(root, warnings),
        "warnings": warnings,
    }


if __name__ == "__main__":
    print(json.dumps(collect(pathlib.Path(__file__).resolve().parents[2]), indent=1))
