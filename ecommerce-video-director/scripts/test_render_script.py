import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys

import render_script


class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scenes = []
        self.words = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "scene" in attrs.get("class", "").split():
            self.scenes.append(attrs["id"])

    def handle_data(self, data):
        self.words.append(data)


SAMPLE = """# 测试脚本
SCR-test｜v01｜待核实

## 创作依据
- 一个事件，两种风格。

## 分镜
| 镜号/时间 | 画面与动作 | 对白 | 声音 |
|---|---|---|---|
| 1 / 0—4秒 | 人物走入 | 你看这里 | 安静 |
| 2 / 4—8秒 | 拉开视角 | 主角是裤子 | 音乐停 |

## 执行
- 保留真实轮廓。
"""


class RenderTests(unittest.TestCase):
    def test_shots_and_content_survive(self):
        reader = Reader()
        reader.feed(render_script.render(SAMPLE))
        self.assertEqual(reader.scenes, ["scene-1", "scene-2"])
        text = " ".join(reader.words)
        for required in ("一个事件，两种风格。", "人物走入", "你看这里", "主角是裤子", "保留真实轮廓。"):
            self.assertIn(required, text)

    def test_raw_html_is_not_executed(self):
        html = render_script.render(SAMPLE + '\n<script>alert("unsafe")</script>\n')
        self.assertNotIn('<script>alert("unsafe")</script>', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn('href="javascript:', render_script.inline('[x](javascript:alert)'))

    def test_bad_shot_table_fails_instead_of_dropping_columns(self):
        with self.assertRaises(ValueError):
            render_script.render(SAMPLE.replace("| 拉开视角 | 主角是裤子 | 音乐停 |", "| 拉开视角 | 主角是裤子 |"))

    def test_cli_preserves_source_and_requires_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "script.md"
            source.write_text(SAMPLE, encoding="utf-8")
            command = [sys.executable, str(Path(render_script.__file__).resolve()), str(source)]
            subprocess.run(command, capture_output=True, check=True)
            self.assertTrue(source.with_suffix(".html").is_file())
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(source.read_text(encoding="utf-8"), SAMPLE)


if __name__ == "__main__":
    unittest.main()
