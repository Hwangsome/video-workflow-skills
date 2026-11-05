#!/usr/bin/env python3
"""Versioned local creative assets. Python standard library only."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import datetime, timezone


STATES = {
    "fact": {"用户提供但未独立核验", "有来源支持", "已过期", "被更正"},
    "pattern": {"待验证", "有观察支持", "多次观察支持", "条件失效"},
    "script": {"创意草案", "待核实", "可拍摄稿"},
    "review": {"待补数据", "观察记录", "可比较记录"},
}
FIELDS = {
    "fact": ("claim", "scope"),
    "pattern": ("mechanism", "applies_when", "avoid_when", "memorable_moment"),
    "script": ("concept", "shots", "target_duration"),
    "review": ("observations", "hypotheses", "limitations", "next_test"),
}


def component(value):
    if not isinstance(value, str) or not re.fullmatch(r"[\w-]{1,80}", value):
        raise ValueError("brand/id 仅允许1—80个字母、数字、中文、下划线或连字符")
    return value


def within(root, *parts):
    root = root.resolve()
    cursor = root
    for part in parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("资产路径不得通过符号链接跨品牌或跨目录")
    result = root.joinpath(*parts).resolve()
    if not result.is_relative_to(root):
        raise ValueError("资产路径越出指定根目录")
    return result


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def lint_shots(content):
    errors = []
    target = content.get("target_duration")
    shots = content.get("shots")
    if not number(target) or target <= 0:
        errors.append("target_duration 必须为正数秒")
    if not isinstance(shots, list) or not shots:
        return errors + ["shots 必须为非空列表"]
    cursor = 0
    for index, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            errors.append(f"镜{index}不是对象")
            continue
        start, end = shot.get("start"), shot.get("end")
        if not number(start) or not number(end) or start < 0 or end <= start:
            errors.append(f"镜{index}时间无效")
            continue
        if abs(start - cursor) > 0.01:
            errors.append(f"镜{index}与上一镜有空隙或重叠（应从{cursor:g}开始）")
        cursor = end
        if not isinstance(shot.get("visual"), str) or not shot["visual"].strip():
            errors.append(f"镜{index}缺少具体画面 visual")
    if number(target) and abs(cursor - target) > 0.01:
        errors.append(f"结束时间{cursor:g}与目标时长{target:g}不符")
    return errors


def validate(record):
    if not isinstance(record, dict):
        raise ValueError("记录必须是JSON对象")
    for key in ("id", "brand"):
        component(record.get(key))
    kind = record.get("kind")
    if not isinstance(kind, str) or kind not in STATES:
        raise ValueError("kind 必须为 fact/pattern/script/review")
    if record.get("status") not in STATES[kind]:
        raise ValueError(f"{kind} 状态不支持：{record.get('status')}")
    if not isinstance(record.get("title"), str) or not record["title"].strip():
        raise ValueError("缺少title")
    for key in ("tags", "sources", "links"):
        values = record.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError(f"{key} 必须为非空字符串组成的列表")
    for link in record.get("links", []):
        component(link)
    content = record.get("content")
    if not isinstance(content, dict):
        raise ValueError("content 必须为对象")
    for key in FIELDS[kind]:
        if key not in content or content[key] in (None, "", [], {}):
            raise ValueError(f"缺少content.{key}；未知内容请明确标记未提供")
    if kind == "fact" and not record.get("sources"):
        raise ValueError("事实必须记录来源；用户提供的信息也应写明来源")
    if kind == "pattern" and record["status"] in {"有观察支持", "多次观察支持"} and not record.get("links"):
        raise ValueError("有观察支持的机制须关联复盘ID")
    if kind == "script":
        if not isinstance(content.get("direction"), str) or not content["direction"].strip():
            raise ValueError("脚本缺少content.direction")
        errors = lint_shots(content)
        if errors:
            raise ValueError("；".join(errors))
        if record["status"] == "可拍摄稿" and content.get("unresolved"):
            raise ValueError("有unresolved待核实事项的脚本不能标为可拍摄稿")


def records(root):
    if not root.exists():
        return []
    result = []
    for path in sorted(root.glob("*/records/*/v*.json")):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"检测到越界符号链接：{path}")
        record = json.loads(path.read_text(encoding="utf-8"))
        validate(record)
        version = record.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ValueError(f"无效版本：{path}")
        if (path.parent.name != record["id"] or path.parent.parent.parent.name != record["brand"]
                or path.name != f"v{version:04d}.json"):
            raise ValueError(f"记录内容与路径不一致：{path}")
        result.append((path, record))
    return result


def latest(items):
    selected = {}
    for path, record in items:
        key = (record["brand"], record["id"])
        if key not in selected or record["version"] > selected[key][1]["version"]:
            selected[key] = (path, record)
    return list(selected.values())


def check_links(record, items):
    available = {r["id"]: r for _, r in latest(items) if r["brand"] == record["brand"]}
    for link in record.get("links", []):
        if link not in available:
            raise ValueError(f"同品牌关联资产不存在：{link}")
    used_assets = record["content"].get("used_assets", [])
    if not isinstance(used_assets, list):
        raise ValueError("used_assets 必须为列表")
    for used in used_assets:
        if (not isinstance(used, dict) or type(used.get("version")) is not int or not any(
            r["brand"] == record["brand"] and r["id"] == used.get("id")
            and r["version"] == used.get("version") for _, r in items
        )):
            raise ValueError(f"引用的具体资产版本不存在：{used}")
    if record["kind"] == "pattern" and record["status"] in {"有观察支持", "多次观察支持"}:
        if not any(available[link]["kind"] == "review" for link in record.get("links", [])):
            raise ValueError("观察支持须关联review资产，而非仅关联脚本")


def add(root, source):
    record = json.loads(source.read_text(encoding="utf-8"))
    validate(record)
    items = records(root)
    check_links(record, items)
    history = [r for _, r in items if r["brand"] == record["brand"] and r["id"] == record["id"]]
    if history and any(r["kind"] != record["kind"] for r in history):
        raise ValueError("同一资产ID不能改变kind")
    version = max((r["version"] for r in history), default=0) + 1
    record.update(version=version, schema_version=1,
                  saved_at=datetime.now(timezone.utc).isoformat())
    destination = within(root, record["brand"], "records", record["id"], f"v{version:04d}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    # Publish complete bytes atomically; concurrent saves cannot overwrite a version.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".pending-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"saved": str(destination), "version": version}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="当前项目资产目录")
    sub = parser.add_subparsers(dest="command", required=True)
    save = sub.add_parser("add", help="保存为新版本，保留旧版本")
    save.add_argument("--input", type=Path, required=True)
    search = sub.add_parser("search", help="检索最新版本")
    search.add_argument("--brand", required=True)
    search.add_argument("--kind", choices=STATES)
    search.add_argument("--tag")
    search.add_argument("--query", default="")
    index = sub.add_parser("index", help="输出派生索引，不改写已有文件")
    index.add_argument("--brand", required=True)
    sub.add_parser("check", help="校验所有版本、时间线与同品牌引用")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "add":
        output = add(root, args.input)
    else:
        items = records(root)
        if args.command == "check":
            for _, record in items:
                check_links(record, items)
            output = {"ok": True, "versions": len(items), "assets": len(latest(items)),
                      "scope": "仅校验结构、时间与引用；不核验事实、创意或效果"}
        else:
            component(args.brand)
            selected = [(p, r) for p, r in latest(items) if r["brand"] == args.brand]
            if args.command == "search":
                selected = [(p, r) for p, r in selected
                            if (not args.kind or r["kind"] == args.kind)
                            and (not args.tag or args.tag in r.get("tags", []))
                            and args.query.casefold() in json.dumps(r, ensure_ascii=False).casefold()]
                output = [r for _, r in selected]
            else:
                output = [{key: r[key] for key in ("id", "kind", "title", "status", "version")}
                          | {"tags": r.get("tags", []), "path": str(p.relative_to(root))}
                          for p, r in selected]
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
