"""
Tests for market.py. Plain unittest, run from the repo root:

    python3 -m unittest tools/desk/test_market.py

The first class reads the real repo and checks the output is sane without
pinning any number: counts are compared with what the same files say when read
a second, independent way. The second feeds collect() a directory with files
missing and checks it degrades instead of raising.
"""
import json
import pathlib
import re
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import market  # noqa: E402

ROOT = HERE.parents[1]
REQUIRED = ["trials", "tests", "grades", "bars", "runs", "strategies", "head", "warnings"]


def _has_source(item):
    return isinstance(item.get("source"), str) and item["source"].startswith("tools/market/")


class RealRepo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = market.collect(ROOT)

    def test_shape_and_json(self):
        for key in REQUIRED:
            self.assertIn(key, self.out)
        json.dumps(self.out)

    def test_no_warnings_on_a_clean_checkout(self):
        self.assertEqual(self.out["warnings"], [])

    def test_trials(self):
        t = self.out["trials"]
        self.assertEqual(t["source"], "tools/market/trials.json")
        self.assertTrue(t["entries"])
        self.assertEqual(t["total"], sum(e["count"] for e in t["entries"]))
        raw = json.loads((ROOT / "tools/market/trials.json").read_text())
        self.assertEqual(t["total"], sum(e["count"] for e in raw["entries"]))
        self.assertEqual(len(t["open_questions"]), len(raw["open_questions_for_the_owner"]))
        for e in t["entries"]:
            for k in ("as_of", "count", "in_ledger", "what", "source"):
                self.assertIn(k, e)
            self.assertTrue(_has_source(e))
            line = int(e["source"].rsplit(":", 1)[1])
            text = (ROOT / "tools/market/trials.json").read_text().splitlines()[line - 1]
            self.assertIn('"as_of"', text)

    def test_tests(self):
        tests = {t["name"]: t for t in self.out["tests"]}
        self.assertEqual(len(tests), 4)
        for t in tests.values():
            for k in ("name", "date", "verdict", "headline", "source"):
                self.assertTrue(t[k], f"{t['name']}: {k} empty")
            self.assertLessEqual(len(t["verdict"]), 200)
            self.assertLessEqual(len(t["headline"]), 200)
            self.assertTrue(re.fullmatch(r"\d{4}-\d{2}-\d{2}", t["date"]))
        self.assertEqual(tests["Cross-section"]["date"], "2026-09-11")
        month = tests["Month-end overlay"]
        self.assertEqual(month["date"], "2026-10-09")
        self.assertIn("PARTIAL", month["verdict"])
        self.assertIn("DO NOT TRADE", month["verdict"])
        self.assertIn("REPLICATES", tests["E-15 replication"]["verdict"])
        self.assertIn("9 of 9", tests["E-15 replication"]["verdict"])  # the nine-file run, not the eight-file one

    def test_test_sources_point_at_the_verdict(self):
        lines = (ROOT / "tools/market/EVIDENCE.md").read_text().splitlines()
        for t in self.out["tests"]:
            path, line = t["source"].rsplit(":", 1)
            self.assertEqual(path, "tools/market/EVIDENCE.md")
            window = " ".join(lines[int(line) - 1:int(line) + 3])
            first_words = " ".join(t["verdict"].split()[:2])
            window = re.sub(r"\s+", " ", re.sub(r"[*`>]", "", window))
            self.assertIn(first_words, window, t["name"])

    def test_grades(self):
        g = self.out["grades"]
        self.assertEqual([x["rank"] for x in g], list(range(1, len(g) + 1)))
        text = (ROOT / "tools/market/EVIDENCE.md").read_text()
        self.assertEqual(len(g), len(re.findall(r"^### \d+ · ", text, re.M)))
        self.assertGreaterEqual(len(g), 15)
        for x in g:
            self.assertTrue(x["idea"] and x["grade"] and _has_source(x))

    def test_bars(self):
        tracked = [p for p in market._git(ROOT, ["ls-files", "tools/market/bars"]).split()
                   if p.endswith(".csv")]
        self.assertEqual(len(self.out["bars"]), len(tracked))
        for b in self.out["bars"]:
            self.assertGreater(b["rows"], 0)
            self.assertLessEqual(b["first_date"], b["last_date"])
            data = [ln for ln in (ROOT / "tools/market/bars" / b["file"]).read_text().splitlines()
                    if re.match(r"\d{4}-\d{2}-\d{2}", ln)]
            self.assertEqual(b["rows"], len(data))
            self.assertTrue(data[0].startswith(b["first_date"]))
            self.assertTrue(data[-1].startswith(b["last_date"]))

    def test_runs(self):
        runs = self.out["runs"]
        self.assertTrue(runs)
        for r in runs:
            self.assertEqual((ROOT / "tools/market/runs" / r["file"]).stat().st_size, r["bytes"])
        self.assertIn("crosstest-2026-09-11.txt", [r["file"] for r in runs])

    def test_strategies(self):
        s = self.out["strategies"]
        self.assertIn("buy_and_hold", s)
        self.assertEqual(len(s), len(set(s)))
        path, line = self.out["strategies_source"].rsplit(":", 1)
        self.assertTrue((ROOT / path).read_text().splitlines()[int(line) - 1].startswith("REGISTRY"))

    def test_head(self):
        h = self.out["head"]
        self.assertRegex(h["commit"], r"^[0-9a-f]{7,}$")
        self.assertRegex(h["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertTrue(h["subject"])


class MissingFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_empty_directory_degrades(self):
        out = market.collect(self.tmp)
        for key in REQUIRED:
            self.assertIn(key, out)
        for key in ("tests", "grades", "bars", "runs", "strategies", "head"):
            self.assertIsNone(out[key], key)
        self.assertIsNone(out["trials"]["total"])
        self.assertIsNone(out["trials"]["entries"])
        self.assertGreaterEqual(len(out["warnings"]), 5)
        self.assertTrue(all(isinstance(w, str) and w for w in out["warnings"]))

    def test_one_missing_file_only_loses_its_own_field(self):
        src = ROOT / "tools/market"
        dst = self.tmp / "tools/market"
        dst.mkdir(parents=True)
        for name in ("EVIDENCE.md", "strategies.py"):
            shutil.copy(src / name, dst / name)            # trials.json is not copied
        out = market.collect(self.tmp)
        self.assertIsNone(out["trials"]["total"])
        self.assertIn("tools/market/trials.json", out["trials"]["source"])
        self.assertTrue(any("trials.json" in w for w in out["warnings"]))
        self.assertEqual(len(out["tests"]), 4)
        self.assertTrue(all(t["verdict"] for t in out["tests"]))
        self.assertTrue(out["grades"])
        self.assertIn("buy_and_hold", out["strategies"])

    def test_heading_missing_from_evidence(self):
        dst = self.tmp / "tools/market"
        dst.mkdir(parents=True)
        (dst / "EVIDENCE.md").write_text("# nothing here\n\n## Each one, in a few lines\n")
        out = market.collect(self.tmp)
        self.assertEqual(len(out["tests"]), 4)
        for t in out["tests"]:
            self.assertIn("verdict", t)
            self.assertIsNone(t["verdict"])
        self.assertEqual(out["grades"], [])
        self.assertTrue(any("no heading" in w for w in out["warnings"]))


if __name__ == "__main__":
    unittest.main()
