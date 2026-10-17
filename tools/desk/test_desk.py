"""python3 -m unittest tools/desk/test_desk.py  (from the repo root)"""
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import desk  # noqa: E402


class CheckActions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "doc.md").write_text("run this:\n    python3 tool.py --go\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_verbatim_command_passes(self):
        acts = [{"id": "a", "source": "doc.md:2", "commands": ["python3 tool.py --go"]}]
        self.assertEqual(desk.check_actions(self.root, acts), [])

    def test_invented_command_is_flagged(self):
        acts = [{"id": "a", "source": "doc.md:2", "commands": ["python3 tool.py --force"]}]
        self.assertEqual(len(desk.check_actions(self.root, acts)), 1)

    def test_missing_source_is_flagged(self):
        acts = [{"id": "a", "source": "nope.md:1", "commands": []}]
        self.assertIn("unreadable", desk.check_actions(self.root, acts)[0])


class Render(unittest.TestCase):
    def test_embeds_json_and_escapes_script_close(self):
        page = desk.render({"x": "</script><b>"}, standalone=False)
        self.assertNotIn("/*DESK*/null", page)
        self.assertNotIn('"</script>', page)
        self.assertFalse(page.lstrip().startswith("<!doctype"))

    def test_standalone_has_doctype(self):
        self.assertTrue(desk.render({}).startswith("<!doctype html>"))


class RealRepo(unittest.TestCase):
    def test_collect_is_json_serialisable(self):
        data = desk.collect()
        json.dumps(data)
        for key in ("market", "etsy", "actions", "generated_at"):
            self.assertIn(key, data)


if __name__ == "__main__":
    unittest.main()
