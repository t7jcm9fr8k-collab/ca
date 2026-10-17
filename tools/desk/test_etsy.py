"""Checks for tools/desk/etsy.py.

    python3 -m unittest tools/desk/test_etsy.py        # from the repo root

Two kinds of test. The first reads the real checkout and asks whether the
output is sane — and where it can, checks it against compose.py and
schedule.py themselves (needs Pillow; skipped without). The second builds
small throwaway repos in a temp dir, takes one file away at a time, and
asserts that collect() answers null plus a warning instead of raising.
"""
import hashlib
import json
import pathlib
import re
import shutil
import struct
import sys
import tempfile
import unittest
import zlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True

import etsy  # noqa: E402

STAGES = {"blocked-provenance", "sources-present", "composed", "qc-passed",
          "qc-blocked", "mocked-up", "listed", "proof-only"}
ETSY = "tools/etsy"


def png_header(w, h):
    """Just enough PNG for a size read: signature + IHDR."""
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr
            + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr)))


def line_of(root, source):
    """The text of repo-relative 'path:line' (or the path alone)."""
    path, _, line = source.partition(":")
    lines = (root / path).read_text().split("\n")
    return lines[int(line) - 1] if line else None


def copy_text_of_etsy(dst, sources=True):
    """A throwaway repo: the real code, catalogue and recipes; sources as empty
    files of the same names (presence is all the collector asks of them)."""
    real = ROOT / ETSY
    out = dst / ETSY
    (out / "recipes").mkdir(parents=True)
    for name in ("compose.py", "listing.py", "names.py", "render_plate.py",
                 "catalogue.json"):
        shutil.copy(real / name, out / name)
    for f in (real / "recipes").glob("*.json"):
        shutil.copy(f, out / "recipes" / f.name)
    if sources:
        (out / "sources").mkdir()
        for f in (real / "sources").iterdir():
            (out / "sources" / f.name).write_bytes(b"")
    return out


class RealRepo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = etsy.collect(ROOT)

    def test_shape(self):
        d = self.d
        for key in ("designs", "listings", "calendar", "sources_dir", "warnings"):
            self.assertIn(key, d)
        json.dumps(d)                                    # serialisable
        self.assertTrue(all(isinstance(w, str) for w in d["warnings"]))
        self.assertTrue(d["designs"], "no designs read from the real repo")

    def test_every_design_is_complete(self):
        ids = [x["id"] for x in self.d["designs"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate design ids")
        for x in self.d["designs"]:
            with self.subTest(design=x["id"]):
                self.assertIn(x["stage"], STAGES)
                self.assertTrue(x["title"])
                self.assertTrue(x["source"])
                self.assertTrue((ROOT / x["source"].partition(":")[0]).exists())
                self.assertIsInstance(x["sources"], list)
                self.assertTrue(x["versions"] is None or isinstance(x["versions"], int))
                if x["stage"] == "blocked-provenance":
                    self.assertTrue(x["blocked_on"])
                if x["stage"] in ("composed", "qc-passed", "listed"):
                    self.assertIsNone(x["blocked_on"])

    def test_sources_point_at_the_lines_they_were_read_from(self):
        seen = 0
        for x in self.d["designs"]:
            for s in x["sources"]:
                seen += 1
                with self.subTest(design=x["id"], plate=s["file"]):
                    self.assertIn(json.dumps(s["file"]), line_of(ROOT, s["source"]))
                    if s["licence"]:
                        self.assertIn('"licence"', line_of(ROOT, s["licence_source"]))
                        self.assertIn(json.dumps(s["licence"]),
                                      line_of(ROOT, s["licence_source"]))
                    self.assertEqual(s["present"],
                                     (ROOT / ETSY / "sources" / s["file"]).is_file())
        self.assertGreater(seen, 0, "no source plates read from any recipe")

    def test_unblocked_designs_have_every_plate(self):
        for x in self.d["designs"]:
            if x["stage"] in ("sources-present", "composed", "mocked-up",
                              "qc-passed", "qc-blocked"):
                with self.subTest(design=x["id"]):
                    self.assertTrue(x["sources"])
                    self.assertTrue(all(s["present"] for s in x["sources"]))
                    self.assertTrue(all(s["licence_verdict"] == "ok" for s in x["sources"]))

    def test_sources_dir_matches_disk(self):
        sd = self.d["sources_dir"]
        self.assertEqual(sd["source"], f"{ETSY}/sources")
        disk = sorted(p.name for p in (ROOT / ETSY / "sources").iterdir() if p.is_file())
        self.assertEqual(sd["files"], disk)
        referenced = {s["file"] for x in self.d["designs"] for s in x["sources"]}
        self.assertEqual(sorted(referenced - set(disk)), sd["missing"])

    def test_listings_roll_up(self):
        lst = self.d["listings"]
        cat = json.loads((ROOT / ETSY / "catalogue.json").read_text())["designs"]
        self.assertEqual(lst["count"], len(cat))
        self.assertIsInstance(lst["errors"], int)
        self.assertEqual(lst["errors"], sum(
            x["listing"]["errors"] for x in self.d["designs"] if x["listing"]))
        self.assertTrue(lst["source"])

    def test_ledger_facts_are_marked_untracked(self):
        for x in self.d["designs"]:
            if x["qc"]:
                self.assertIs(x["qc"]["tracked"], False)
                self.assertIn("history.json", x["qc"]["source"])
        if self.d["ledger"]["present"] and self.d["ledger"]["tracked"] is not None:
            self.assertIs(self.d["ledger"]["tracked"], False)

    def test_tracked_flags_agree_with_git(self):
        plates = [s for x in self.d["designs"] for s in x["sources"] if s["present"]]
        if not plates or plates[0]["tracked"] is None:
            self.skipTest("git could not say what is tracked")
        import subprocess
        listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", ETSY],
                                capture_output=True).stdout.decode().split("\0")
        for s in plates:
            self.assertEqual(s["tracked"], f"{ETSY}/sources/{s['file']}" in listed)

    def test_agrees_with_compose_and_schedule(self):
        """The independent oracle: schedule.renderable() is what the pipeline
        itself calls 'can be rendered today'."""
        cat = json.loads((ROOT / ETSY / "catalogue.json").read_text())["designs"]
        sys.path.insert(0, str(ROOT / ETSY))
        try:
            import schedule as pipeline_schedule
            ready = pipeline_schedule.renderable(cat)
        except ImportError:
            self.skipTest("Pillow not installed; schedule.py cannot be imported")
        finally:
            sys.path.remove(str(ROOT / ETSY))
        for x in self.d["designs"]:
            row = next((c for c in cat if c["id"] == x["id"]), None)
            if row is None or row["status"] == "live":
                continue
            with self.subTest(design=x["id"]):
                self.assertEqual(x["stage"] != "blocked-provenance", x["id"] in ready)


class Degrades(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def assertWarned(self, d, *words):
        text = " | ".join(d["warnings"])
        self.assertTrue(d["warnings"], "no warning where a file was missing")
        for w in words:
            self.assertIn(w, text)

    def design(self, d, did):
        return next(x for x in d["designs"] if x["id"] == did)

    def test_empty_directory(self):
        d = etsy.collect(self.tmp)
        self.assertEqual(d["designs"], [])
        self.assertIsNone(d["listings"])
        self.assertIsNone(d["calendar"])
        self.assertIsNone(d["sources_dir"]["files"])
        self.assertWarned(d, "catalogue.json", "sources")

    def test_nonexistent_root(self):
        d = etsy.collect(self.tmp / "nowhere")
        self.assertEqual(d["designs"], [])
        self.assertTrue(d["warnings"])

    def test_no_sources_dir_blocks_every_planned_design(self):
        copy_text_of_etsy(self.tmp, sources=False)
        d = etsy.collect(self.tmp)
        planned = [x for x in d["designs"] if x["catalogue_status"] == "planned"]
        self.assertTrue(planned)
        for x in planned:
            self.assertEqual(x["stage"], "blocked-provenance")
            self.assertIn("no source plate in tools/etsy/sources/", x["blocked_on"])
            self.assertTrue(all(s["present"] is False for s in x["sources"]))
        self.assertIsNone(d["sources_dir"]["files"])
        self.assertWarned(d, "sources")

    def test_one_missing_plate_blocks_only_its_design(self):
        etsy_dir = copy_text_of_etsy(self.tmp)
        recipe = json.loads((etsy_dir / "recipes" / "orchid-skull.json").read_text())
        gone = recipe["layers"][0]["source"]
        (etsy_dir / "sources" / gone).unlink()
        d = etsy.collect(self.tmp)
        x = self.design(d, "orchid-skull")
        self.assertEqual(x["stage"], "blocked-provenance")
        self.assertIn(gone, x["blocked_on"])
        self.assertIn(recipe["layers"][0]["_wanted"], x["blocked_on"])
        self.assertFalse(next(s for s in x["sources"] if s["file"] == gone)["present"])
        self.assertIn(gone, d["sources_dir"]["missing"])
        self.assertEqual(self.design(d, "kraken-chart")["stage"], "sources-present")

    def test_blank_provenance_is_blocked(self):
        etsy_dir = copy_text_of_etsy(self.tmp)
        p = etsy_dir / "recipes" / "kraken-chart.json"
        r = json.loads(p.read_text())
        r["layers"][1]["provenance"]["licence"] = "CC-BY-SA 4.0"
        r["layers"][0]["provenance"]["url"] = ""
        p.write_text(json.dumps(r))
        x = self.design(etsy.collect(self.tmp), "kraken-chart")
        self.assertEqual(x["stage"], "blocked-provenance")
        self.assertIn("provenance.url is empty", x["blocked_on"])
        self.assertIn("CC-BY-SA", x["blocked_on"])

    def test_missing_recipe_file(self):
        etsy_dir = copy_text_of_etsy(self.tmp)
        (etsy_dir / "recipes" / "dore-descent.json").unlink()
        d = etsy.collect(self.tmp)
        x = self.design(d, "dore-descent")
        self.assertEqual(x["stage"], "blocked-provenance")
        self.assertEqual(x["sources"], [])
        self.assertIn("missing", x["blocked_on"])
        self.assertWarned(d, "dore-descent.json")

    def test_unreadable_recipe_file(self):
        etsy_dir = copy_text_of_etsy(self.tmp)
        (etsy_dir / "recipes" / "dore-descent.json").write_text("{not json")
        d = etsy.collect(self.tmp)
        self.assertEqual(self.design(d, "dore-descent")["stage"], "blocked-provenance")
        self.assertWarned(d, "dore-descent.json")

    def test_missing_catalogue(self):
        etsy_dir = copy_text_of_etsy(self.tmp)
        (etsy_dir / "catalogue.json").unlink()
        d = etsy.collect(self.tmp)
        self.assertIsNone(d["listings"])
        self.assertTrue(all(x["stage"] == "proof-only" for x in d["designs"]))
        self.assertWarned(d, "catalogue.json")

    def test_missing_gate_source(self):
        etsy_dir = copy_text_of_etsy(self.tmp)
        (etsy_dir / "compose.py").unlink()
        d = etsy.collect(self.tmp)
        x = self.design(d, "orchid-skull")
        self.assertEqual(x["stage"], "blocked-provenance")
        self.assertIn("could not be checked", x["blocked_on"])
        self.assertWarned(d, "compose.py")

    def test_missing_listing_py(self):
        etsy_dir = copy_text_of_etsy(self.tmp)
        (etsy_dir / "listing.py").unlink()
        d = etsy.collect(self.tmp)
        self.assertIsNone(d["listings"])
        self.assertWarned(d, "listing.py")

    def test_missing_ledger_is_null_not_zero(self):
        copy_text_of_etsy(self.tmp)
        d = etsy.collect(self.tmp)
        x = self.design(d, "orchid-skull")
        self.assertIsNone(x["versions"])
        self.assertIsNone(x["qc"])
        self.assertFalse(d["ledger"]["present"])
        self.assertWarned(d, "history.json")

    def test_corrupt_ledger(self):
        etsy_dir = copy_text_of_etsy(self.tmp)
        (etsy_dir / "out").mkdir()
        (etsy_dir / "out" / "history.json").write_text("{{{")
        d = etsy.collect(self.tmp)
        self.assertIsNone(self.design(d, "orchid-skull")["versions"])
        self.assertWarned(d, "history.json")

    def test_missing_calendar_is_null(self):
        copy_text_of_etsy(self.tmp)
        d = etsy.collect(self.tmp)
        self.assertIsNone(d["calendar"])
        self.assertWarned(d, "calendar")

    def test_outside_git_tracked_is_null(self):
        copy_text_of_etsy(self.tmp)
        d = etsy.collect(self.tmp)
        self.assertTrue(all(s["tracked"] is None for x in d["designs"]
                            for s in x["sources"]))
        self.assertWarned(d, "git")


class Stages(unittest.TestCase):
    """Fake out/ evidence, to walk a design up the stages."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.etsy = copy_text_of_etsy(self.tmp)
        self.out = self.etsy / "out"
        self.out.mkdir()
        self.canvas = etsy._load_defs(self.etsy / "compose.py", [])["CANVAS"]

    def stage(self, did="orchid-skull"):
        d = etsy.collect(self.tmp)
        return next(x for x in d["designs"] if x["id"] == did)

    def render(self, size, did="orchid-skull"):
        for way in ("onlight", "ondark"):
            (self.out / f"{did}-{way}.png").write_bytes(png_header(*size))

    def ledger(self, verdict, print_bytes=b"print", tamper=False, did="orchid-skull",
               failed=()):
        f = self.out / f"{did}-v1-onlight.png"
        f.write_bytes(print_bytes)
        sha = hashlib.sha256(print_bytes).hexdigest()
        if tamper:
            f.write_bytes(b"changed afterwards")
        checks = {"ink coverage": {"ok": verdict != "blocked", "value": "6.2%",
                                   "want": "8%-55%"}}
        led = {"designs": {did: {
            "versions": [{"version": 1, "files": {}, "changes": []}],
            "inspections": [{"version": 1, "verdict": verdict, "failed": list(failed),
                             "unrun": [], "checks": checks,
                             "file": f"out/{f.name}", "sha256": sha}]}}}
        (self.out / "history.json").write_text(json.dumps(led, indent=2))

    def test_draft_render_is_not_composed(self):
        self.render((self.canvas[0] // 5, self.canvas[1] // 5))
        x = self.stage()
        self.assertEqual(x["stage"], "sources-present")
        self.assertTrue(x["render"]["draft"])
        self.assertIn("draft", x["blocked_on"])

    def test_full_render_is_composed(self):
        self.render(self.canvas)
        x = self.stage()
        self.assertEqual(x["stage"], "composed")
        self.assertFalse(x["render"]["draft"])
        self.assertIn("orchid-skull-onlight.png", x["render"]["files"][0])

    def test_qc_passed(self):
        self.render(self.canvas)
        self.ledger("pass")
        x = self.stage()
        self.assertEqual((x["stage"], x["versions"]), ("qc-passed", 1))
        self.assertEqual(x["qc"]["file_state"], "ok")
        self.assertIs(x["qc"]["tracked"], False)

    def test_qc_blocked_says_what_failed(self):
        self.ledger("blocked", failed=["ink coverage"])
        x = self.stage()
        self.assertEqual(x["stage"], "qc-blocked")
        self.assertIn("ink coverage 6.2%", x["blocked_on"])
        self.assertIn("8%-55%", x["blocked_on"])

    def test_pass_on_a_file_that_changed_does_not_count(self):
        self.ledger("pass", tamper=True)
        x = self.stage()
        self.assertEqual(x["stage"], "mocked-up")
        self.assertEqual(x["qc"]["file_state"], "changed")
        self.assertIn("changed", x["blocked_on"])

    def test_version_with_no_inspection_is_mocked_up(self):
        (self.out / "history.json").write_text(json.dumps(
            {"designs": {"orchid-skull": {"versions": [{"version": 1}],
                                          "inspections": []}}}))
        x = self.stage()
        self.assertEqual(x["stage"], "mocked-up")
        self.assertIsNone(x["qc"])
        self.assertIn("no recorded QC", x["blocked_on"])

    def test_ledger_without_this_design_is_zero_versions(self):
        (self.out / "history.json").write_text(json.dumps({"designs": {}}))
        x = self.stage()
        self.assertEqual(x["versions"], 0)
        self.assertIsNone(x["qc"])

    def test_live_status_wins(self):
        self.ledger("blocked", failed=["ink coverage"])
        cat = json.loads((self.etsy / "catalogue.json").read_text())
        next(d for d in cat["designs"] if d["id"] == "orchid-skull")["status"] = "live"
        (self.etsy / "catalogue.json").write_text(json.dumps(cat))
        self.assertEqual(self.stage()["stage"], "listed")

    def test_calendar_is_counted_from_the_file(self):
        (self.out / "calendar.md").write_text(
            "# Release and posting calendar\n\n"
            "| Date | Design | Why then |\n|---|---|---|\n"
            "| 2026-10-04 | Orchid Skull | spread for the ranking boost |\n"
            "| 2026-10-11 | Kraken Chart | **BLOCKED — no plates / provenance blank**; x |\n"
            "\n**2026-10-06 Tue · 10:30 · Pinterest · Orchid Skull**  \nShot: x  \n"
            "\n**2026-10-09 Fri · 20:30 · TikTok · Orchid Skull**  \nShot: y  \n")
        cal = etsy.collect(self.tmp)["calendar"]
        self.assertEqual(cal["slots"], 2)
        self.assertEqual((cal["first"], cal["last"]), ("2026-10-06", "2026-10-09"))
        self.assertEqual((cal["releases"], cal["releases_blocked"]), (2, 1))
        self.assertEqual(cal["file"], f"{ETSY}/out/calendar.md")


if __name__ == "__main__":
    unittest.main()
