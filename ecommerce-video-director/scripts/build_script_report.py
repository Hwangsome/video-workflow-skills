#!/usr/bin/env python3
"""Build script.md and report.html from one script.json; standard library only."""

import argparse
import json
import math
from pathlib import Path
import sys

from asset_store import lint_shots
from render_script import render


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}必须为非空文字")


def strings(value, name):
    if not isinstance(value, list):
        raise ValueError(f"{name}必须为列表")
    for item in value:
        text(item, name)


def validate(data, planning=None):
    if not isinstance(data, dict):
        raise ValueError("输入必须是JSON对象")
    for key in ("asset_id", "title", "status"):
        text(data.get(key), key)
    if type(data.get("version")) is not int or data["version"] < 1:
        raise ValueError("version必须为正整数")
    ref = data.get("planning_ref", {})
    if not isinstance(ref, dict):
        raise ValueError("缺少planning_ref")
    for key in ("asset_id", "concept_id", "source"):
        text(ref.get(key), "planning_ref." + key)
    if type(ref.get("version")) is not int or ref["version"] < 1:
        raise ValueError("上游版本必须为正整数")
    if planning is not None:
        if not isinstance(planning, dict) or not isinstance(planning.get("concepts"), list) or any(not isinstance(c, dict) for c in planning["concepts"]):
            raise ValueError("上游策划必须为对象，concepts必须为概念对象列表")
        if (planning.get("asset_id") != ref["asset_id"] or planning.get("version") != ref["version"]
                or ref["concept_id"] not in [c.get("concept_id") for c in planning.get("concepts", [])]):
            raise ValueError("上游策划ID、版本或concept_id不匹配")
    if not isinstance(data.get("story"), dict):
        raise ValueError("缺少story")
    for key in ("one_sentence", "promise"):
        text(data["story"].get(key), "story." + key)
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("segments必须为非空列表")
    ids = set()
    claims = data.get("claim_checks")
    if not isinstance(claims, list):
        raise ValueError("claim_checks必须为列表")
    claim_ids = {}
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError("主张必须为对象")
        for key in ("id", "statement", "source", "status", "scope"):
            text(claim.get(key), "claim." + key)
        if claim["id"] in claim_ids or claim["status"] not in ("已支持", "待核实", "已删除"):
            raise ValueError("主张ID重复或状态无效")
        claim_ids[claim["id"]] = claim
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("内容段必须是对象")
        for key in ("id", "location", "action", "visual", "voiceover", "beat", "emotion"):
            text(segment.get(key), "segment." + key)
        if segment["id"] in ids:
            raise ValueError("内容段ID重复")
        ids.add(segment["id"])
        for key in ("characters", "sound", "screen_text", "claim_ids"):
            strings(segment.get(key), "segment." + key)
        if not isinstance(segment.get("dialogue"), list):
            raise ValueError("dialogue必须为列表，无对白时用空列表")
        for speech in segment["dialogue"]:
            if not isinstance(speech, dict):
                raise ValueError("对白必须为角色和完整台词对象")
            text(speech.get("character"), "dialogue.character")
            text(speech.get("text"), "dialogue.text")
            if speech["character"] not in segment["characters"]:
                raise ValueError(f'{segment["id"]}对白角色未列入人物；画外角色也须标明')
        for cid in segment["claim_ids"]:
            if cid not in claim_ids or claim_ids[cid]["status"] != "已支持":
                raise ValueError(f"主稿关联未支持或不存在的主张：{cid}")
    errors = lint_shots({"target_duration": data.get("target_duration"), "shots": [
        {"start": s.get("start"), "end": s.get("end"), "visual": s["visual"]} for s in segments]})
    if errors:
        raise ValueError("；".join(errors))
    if "pacing_model" in data:
        validate_pacing(data, ids)
    alternatives = data.get("alternatives", {})
    notes = data.get("alternative_notes", {})
    if not isinstance(notes, dict):
        raise ValueError("alternative_notes必须为对象")
    if not isinstance(alternatives, dict):
        raise ValueError("alternatives必须为对象")
    for category in ("openings", "key_claims", "endings"):
        items = alternatives.get(category)
        if not isinstance(items, list):
            raise ValueError(f"alternatives.{category}必须为列表")
        if not items:
            text(notes.get(category), "备选不适用理由")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("备选必须为对象")
            for key in ("text", "when_to_use", "difference", "impact"):
                text(item.get(key), "alternative." + key)
    handoff = data.get("handoff", {})
    if not isinstance(handoff, dict):
        raise ValueError("handoff必须为对象")
    for key in ("must_keep", "can_change", "props", "pending_facts", "simplified_version"):
        strings(handoff.get(key), "handoff." + key)
        if key != "pending_facts" and not handoff[key]:
            raise ValueError(f"handoff.{key}需有决定或不适用理由")
    checks = data.get("self_check", {})
    if not isinstance(checks, dict):
        raise ValueError("self_check必须为对象")
    for key in ("readthrough", "action_timing", "shootability", "promise_payoff", "claims"):
        item = checks.get(key)
        if not isinstance(item, dict):
            raise ValueError(f"缺少self_check.{key}")
        for field in ("status", "method", "result"):
            text(item.get(field), "self_check." + key + "." + field)


def validate_pacing(data, segment_ids):
    if data["pacing_model"] != "event-driven-v1":
        raise ValueError("不支持的pacing_model")
    for segment in data["segments"]:
        pacing = segment.get("pacing")
        if not isinstance(pacing, dict):
            raise ValueError(f'{segment["id"]}缺少pacing')
        for key in ("hold_reason", "edit_intent"):
            text(pacing.get(key), "pacing." + key)
        events = pacing.get("progression")
        if not isinstance(events, list) or not events:
            raise ValueError("progression必须有可观察事件")
        previous = -1
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                raise ValueError("推进点必须为对象")
            at = event.get("at")
            if (type(at) not in (int, float) or not math.isfinite(at) or at < 0
                    or at >= segment["end"] - segment["start"] or at <= previous
                    or (index == 0 and at != 0)):
                raise ValueError("段内推进时间必须从0起、严格递增且小于本段时长")
            text(event.get("event"), "progression.event")
            previous = at
    pacing_check = data.get("self_check", {}).get("pacing") if isinstance(data.get("self_check"), dict) else None
    if not isinstance(pacing_check, dict):
        raise ValueError("缺少self_check.pacing")
    for key in ("status", "method", "result"):
        text(pacing_check.get(key), "self_check.pacing." + key)
    review = data.get("editorial_review")
    if not isinstance(review, dict):
        raise ValueError("缺少editorial_review")
    if review.get("mode") not in ("independent-agent", "self-review", "not-run"):
        raise ValueError("审查方式无效")
    if review.get("reviewed_asset_id") != data["asset_id"] or review.get("reviewed_version") != data["version"]:
        raise ValueError("审查必须对应当前脚本ID和版本，不能沿用旧版结论")
    if review.get("verdict") not in ("通过", "需改", "待核实", "未执行"):
        raise ValueError("审查结论无效")
    if (review["mode"] == "not-run") != (review["verdict"] == "未执行"):
        raise ValueError("未执行审查不能记录已审结论")
    for key in ("reviewer", "pacing_summary"):
        text(review.get(key), "editorial_review." + key)
    strings(review.get("limitations"), "editorial_review.limitations")
    findings = review.get("findings")
    if not isinstance(findings, list):
        raise ValueError("审稿findings必须为列表")
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("审稿问题必须为对象")
        strings(finding.get("segment_ids"), "finding.segment_ids")
        if not finding["segment_ids"] or any(s not in segment_ids for s in finding["segment_ids"]):
            raise ValueError("审稿问题必须关联本稿实际段号")
        for key in ("issue", "impact", "change", "reason"):
            text(finding.get(key), "finding." + key)
        if finding.get("status") not in ("已修正", "保留并说明", "待处理"):
            raise ValueError("审稿问题处理状态无效")
    if review["verdict"] == "通过" and any(f["status"] == "待处理" for f in findings):
        raise ValueError("仍有待处理问题不能标审查通过")


def cell(value):
    return str(value).replace("\r", " ").replace("\n", " / ").replace("|", r"\|")


def table(headers, rows):
    return ["| " + " | ".join(map(cell, headers)) + " |",
            "|" + "---|" * len(headers)] + ["| " + " | ".join(map(cell, row)) + " |" for row in rows]


def markdown(data):
    ref = data["planning_ref"]
    lines = [f'# {cell(data["title"])}',
             f'{cell(data["asset_id"])}｜v{data["version"]:02d}｜{data["target_duration"]:g}秒｜{cell(data["status"])}',
             "", "## 01 一句话故事与核心承诺", "",
             "- 故事：" + cell(data["story"]["one_sentence"]),
             "- 核心承诺：" + cell(data["story"]["promise"]),
             f'- 上游策划：{cell(ref["asset_id"])} / v{ref["version"]} / {cell(ref["concept_id"])}',
             '- 策划出处：' + cell(ref["source"]),
             "", "## 02 完整视听脚本"]
    lines += table(["段号/时间", "场景与人物", "可表演动作与画面", "角色完整台词", "旁白", "关键声音/停顿", "屏幕文字"], [
        [f'{s["id"]} / {s["start"]:g}—{s["end"]:g}秒', s["location"] + "；" + "、".join(s["characters"]),
         s["action"] + "；画面：" + s["visual"],
         " / ".join(x["character"] + "：" + x["text"] for x in s["dialogue"]) or "无对白",
         s["voiceover"], " / ".join(s["sound"]) or "无", " / ".join(s["screen_text"]) or "无"] for s in data["segments"]])
    lines += ["", "## 03 叙事与情绪节奏"]
    lines += table(["段落", "叙事功能/信息转折", "情绪与触发"], [[s["id"], s["beat"], s["emotion"]] for s in data["segments"]])
    if data.get("pacing_model") == "event-driven-v1":
        lines += ["", "### 内容段不是单镜头", "以下为段内内容推进的编排估计，不是实测用时或最终分镜。"]
        for segment in data["segments"]:
            pacing = segment["pacing"]
            lines += ["", "### " + segment["id"] + " · 段内节奏"]
            lines += table(["段内秒数（估计）", "可感知变化"], [[f'{e["at"]:g}', e["event"]] for e in pacing["progression"]])
            lines += ["", "- 停留理由：" + cell(pacing["hold_reason"]), "- 衔接建议：" + cell(pacing["edit_intent"])]
    lines += ["", "## 04 文案备选"]
    for category, title in (("openings", "开场"), ("key_claims", "关键卖点表达"), ("endings", "结尾")):
        lines += ["### " + title]
        options = data["alternatives"][category]
        if options:
            lines += table(["备选文案", "适用条件", "实质差异", "替换影响"], [[o[k] for k in ("text", "when_to_use", "difference", "impact")] for o in options])
        else:
            lines.append(cell(data["alternative_notes"][category]))
    lines += ["", "## 05 制作交接说明"]
    for key, title in (("must_keep", "必须保留"), ("can_change", "可以调整"), ("props", "必要道具"),
                       ("pending_facts", "事实待核实项"), ("simplified_version", "简化拍法")):
        lines += ["### " + title, ""] + ["- " + cell(v) for v in data["handoff"][key]]
        if not data["handoff"][key]:
            lines.append("无已列出的待核实项；不代表工具已独立核验事实。")
    lines += ["", "## 06 脚本自检结果"]
    labels = {"readthrough": "台词试读", "action_timing": "真实操作时间", "shootability": "动作可拍性", "promise_payoff": "承诺兑现", "claims": "产品主张依据"}
    if data.get("pacing_model") == "event-driven-v1":
        labels["pacing"] = "过空/过满与自然行为"
    lines += table(["检查项", "状态", "检查方式", "结果/未完成项"], [[label] + [data["self_check"][key][f] for f in ("status", "method", "result")] for key, label in labels.items()])
    lines += ["### 主张对应依据"]
    lines += table(["ID", "主张", "来源", "状态", "适用范围"], [[c[k] for k in ("id", "statement", "source", "status", "scope")] for c in data["claim_checks"]])
    if not data["claim_checks"]:
        lines.append("无列出的确定性产品主张；仍需核对画面是否暗示未经支持的能力。")
    if data.get("pacing_model") == "event-driven-v1":
        review = data["editorial_review"]
        lines += ["", "### 审稿与修订记录", "",
                  f'- 方式：{cell(review["mode"])}；审稿者：{cell(review["reviewer"])}',
                  f'- 对应：{cell(review["reviewed_asset_id"])} / v{review["reviewed_version"]}；结论：{cell(review["verdict"])}',
                  '- 节奏判断：' + cell(review["pacing_summary"])]
        lines += table(["段落", "问题", "影响", "修改/保留", "状态", "理由"], [["、".join(f["segment_ids"])] + [f[k] for k in ("issue", "impact", "change", "status", "reason")] for f in review["findings"]])
        lines += ["", "### 审查限制", ""] + ["- " + cell(v) for v in review["limitations"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--planning", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.source.read_text(encoding="utf-8"))
    planning = json.loads(args.planning.read_text(encoding="utf-8")) if args.planning else None
    validate(data, planning)
    md, html = args.source.parent / "script.md", args.source.parent / "report.html"
    if args.source.resolve() in (md.resolve(), html.resolve()):
        raise ValueError("输出不能覆盖源数据")
    if not args.overwrite and (md.exists() or html.exists()):
        raise ValueError("派生产物已存在；先核对内容再用--overwrite，或另存版本目录")
    content = markdown(data)
    document = render(content)
    md.write_text(content, encoding="utf-8")
    html.write_text(document, encoding="utf-8")
    print(json.dumps({"json": str(args.source.resolve()), "markdown": str(md.resolve()),
                      "html": str(html.resolve()), "upstream_checked": planning is not None}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
