"""Run: python3 -m unittest discover -s scripts -p 'test_*.py' -v"""

import copy
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch

import asset_store as store


class AssetStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / "content-assets"
        example = Path(__file__).resolve().parents[1] / "assets/script-record.example.json"
        self.sample = json.loads(example.read_text(encoding="utf-8"))

    def save(self, record):
        source = self.workspace / "input.json"
        source.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return store.add(self.root, source)

    def test_versions_preserve_history(self):
        first = self.save(self.sample)
        modified = copy.deepcopy(self.sample)
        modified["title"] = "第二版"
        second = self.save(modified)
        self.assertEqual(second["version"], 2)
        self.assertEqual(json.loads(Path(first["saved"]).read_text())["title"], self.sample["title"])
        self.assertEqual(store.latest(store.records(self.root))[0][1]["title"], "第二版")

    def test_completed_plan_and_pending_production_are_separate(self):
        record = copy.deepcopy(self.sample)
        record["status"] = "方案完成"
        record["content"]["critical_inputs_missing"] = []
        record["content"]["production_readiness"] = "待落实"
        with self.assertRaises(ValueError):
            self.save(record)
        record["content"]["plan_sections"] = {key: f"方案.md#{key}" for key in
            ("brief", "strategy", "concept", "copy", "direction", "storyboard", "production", "handoff")}
        self.save(record)
        record["content"]["critical_inputs_missing"] = ["商品结构未知"]
        with self.assertRaises(ValueError):
            self.save(record)

    def test_three_role_plan_does_not_require_production(self):
        record = copy.deepcopy(self.sample)
        record["status"] = "方案完成"
        record["content"].update(plan_model="preproduction-three-role-v1", critical_inputs_missing=[],
            plan_sections={key: f"方案.md#{key}" for key in ("planning", "research", "writing")},
            verification_summary="产品依据来自用户资料；外部音乐未使用；无实测结论")
        self.save(record)
        del record["content"]["plan_sections"]["research"]
        with self.assertRaises(ValueError):
            self.save(record)

    def test_reject_path_traversal_and_symlink(self):
        for value in ("../outside", "/tmp/example", "demo/name", ".."):
            record = copy.deepcopy(self.sample)
            record["brand"] = value
            with self.assertRaises(ValueError):
                self.save(record)
        self.root.mkdir()
        outside = self.workspace / "outside"
        outside.mkdir()
        (self.root / "demo").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.save(self.sample)
        self.assertEqual(list(outside.iterdir()), [])

    def test_reject_invalid_timeline(self):
        for change in ({"start": 5}, {"end": -1}, {"start": float("nan")}, {"visual": ""}):
            record = copy.deepcopy(self.sample)
            record["content"]["shots"][1].update(change)
            with self.assertRaises(ValueError):
                self.save(record)

    def test_reject_unresolved_ready_script(self):
        self.sample["status"] = "可拍摄稿"
        with self.assertRaises(ValueError):
            self.save(self.sample)

    def test_brand_scoped_links_and_exact_versions(self):
        self.save(self.sample)
        other = copy.deepcopy(self.sample)
        other.update(id="SCR-other", brand="other", links=[self.sample["id"]])
        with self.assertRaises(ValueError):
            self.save(other)
        other.update(brand="demo", links=[])
        other["content"]["used_assets"] = [{"id": self.sample["id"], "version": 99}]
        with self.assertRaises(ValueError):
            self.save(other)
        other["content"]["used_assets"][0]["version"] = 1
        self.save(other)

    def test_observed_pattern_requires_review(self):
        record = {"id": "PAT-001", "brand": "demo", "kind": "pattern", "title": "拟人",
                  "status": "有观察支持", "links": [], "content": {
                      "mechanism": "拟人", "applies_when": "形态变化", "avoid_when": "不接受拟人",
                      "memorable_moment": "折叠即下班"}}
        with self.assertRaises(ValueError):
            self.save(record)
        self.save(self.sample)
        record["links"] = [self.sample["id"]]
        with self.assertRaises(ValueError):
            self.save(record)
        review = {"id": "REV-001", "brand": "demo", "kind": "review", "title": "试拍反馈",
                  "status": "观察记录", "content": {"observations": "纸片字不清楚",
                      "hypotheses": "字号过小", "limitations": "仅现场观察无上线数据",
                      "next_test": "放大字卡试拍"}}
        self.save(review)
        record["links"] = ["REV-001"]
        self.save(record)

    def test_no_source_fact_and_empty_query_are_not_written(self):
        fact = {"id": "FACT-001", "brand": "demo", "kind": "fact", "title": "可折叠",
                "status": "用户提供但未独立核验", "content": {"claim": "可折叠", "scope": "待确认SKU"}}
        with self.assertRaises(ValueError):
            self.save(fact)
        self.assertEqual(store.records(self.root), [])
        self.assertFalse(self.root.exists())

    def test_failed_publish_leaves_no_partial_record(self):
        with patch.object(store.os, "link", side_effect=FileExistsError("concurrent save")):
            with self.assertRaises(FileExistsError):
                self.save(self.sample)
        self.assertEqual(store.records(self.root), [])
        self.assertEqual(list(self.root.rglob(".pending-*")), [])

    def test_command_line_roundtrip(self):
        source = self.workspace / "record.json"
        source.write_text(json.dumps(self.sample), encoding="utf-8")
        executable = Path(store.__file__).resolve()

        def cli(*args):
            result = subprocess.run([sys.executable, str(executable), "--root", str(self.root), *args],
                                    text=True, capture_output=True, check=True)
            return json.loads(result.stdout)

        self.assertEqual(cli("add", "--input", str(source))["version"], 1)
        self.assertEqual(cli("add", "--input", str(source))["version"], 2)
        self.assertEqual(len(cli("index", "--brand", "demo")), 1)
        self.assertEqual(len(cli("search", "--brand", "demo", "--tag", "搞怪")), 1)
        self.assertEqual(cli("search", "--brand", "other"), [])
        self.assertTrue(cli("check")["ok"])


if __name__ == "__main__":
    unittest.main()
