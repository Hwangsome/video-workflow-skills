import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import build_script_report as builder
from test_render_script import Reader


EXAMPLE = Path(__file__).resolve().parents[1] / "examples/07-script-package/script.json"


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_all_script_information_survives_rendering(self):
        builder.validate(self.data)
        reader = Reader()
        reader.feed(builder.render(builder.markdown(self.data)))
        words = " ".join(reader.words)
        self.assertEqual(len(reader.scenes), len(self.data["segments"]))
        for segment in self.data["segments"]:
            for key in ("location", "action", "visual", "voiceover", "beat", "emotion"):
                self.assertIn(segment[key], words)
            for key in ("sound", "screen_text"):
                for item in segment[key]:
                    self.assertIn(item, words)
        for group in self.data["alternatives"].values():
            for item in group:
                for value in item.values():
                    self.assertIn(value, words)
        for items in self.data["handoff"].values():
            for item in items:
                self.assertIn(item, words)
        for check in self.data["self_check"].values():
            for value in check.values():
                self.assertIn(value, words)

    def test_actual_upstream_identity_and_concept_are_checked(self):
        ref = self.data["planning_ref"]
        upstream = {"asset_id": ref["asset_id"], "version": ref["version"], "concepts": [{"concept_id": ref["concept_id"]}]}
        builder.validate(self.data, upstream)
        for key, value in (("asset_id", "other"), ("version", 2), ("concepts", [])):
            bad = copy.deepcopy(upstream)
            bad[key] = value
            with self.assertRaisesRegex(ValueError, "不匹配"):
                builder.validate(self.data, bad)

    def test_pending_claim_cannot_enter_main_script(self):
        self.data["claim_checks"][0]["status"] = "待核实"
        with self.assertRaisesRegex(ValueError, "未支持"):
            builder.validate(self.data)

    def test_unassigned_dialogue_character_is_rejected(self):
        self.data["segments"][0]["dialogue"] = [{"character": "未交代的画外人物", "text": "等等。"}]
        with self.assertRaisesRegex(ValueError, "对白角色"):
            builder.validate(self.data)

    def test_upstream_requires_locatable_source(self):
        del self.data["planning_ref"]["source"]
        with self.assertRaisesRegex(ValueError, "source"):
            builder.validate(self.data)

    def test_gap_and_duration_mismatch_are_rejected(self):
        self.data["segments"][1]["start"] += 1
        with self.assertRaises(ValueError):
            builder.validate(self.data)
        self.setUp()
        self.data["target_duration"] = 31
        with self.assertRaises(ValueError):
            builder.validate(self.data)

    def test_malformed_supporting_objects_fail_cleanly(self):
        for key in ("handoff", "self_check", "alternative_notes"):
            bad = copy.deepcopy(self.data)
            bad[key] = []
            with self.assertRaises(ValueError):
                builder.validate(bad)

    def test_empty_alternatives_require_explanation(self):
        self.data["alternatives"]["openings"] = []
        with self.assertRaises(ValueError):
            builder.validate(self.data)
        self.data["alternative_notes"] = {"openings": "本次锁定法定披露开场，不另拟。"}
        builder.validate(self.data)

    def test_cli_no_partial_output_on_bad_input_and_no_silent_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "script.json"
            command = [sys.executable, str(Path(builder.__file__).resolve()), str(source)]
            source.write_text("{}", encoding="utf-8")
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(list(Path(folder).iterdir()), [source])
            raw = json.dumps(self.data, ensure_ascii=False)
            source.write_text(raw, encoding="utf-8")
            subprocess.run(command, check=True, capture_output=True)
            md = Path(folder) / "script.md"
            self.assertTrue((Path(folder) / "report.html").exists())
            md.write_text("独立修改", encoding="utf-8")
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(md.read_text(encoding="utf-8"), "独立修改")
            self.assertEqual(source.read_text(encoding="utf-8"), raw)


if __name__ == "__main__":
    unittest.main()
