#!/usr/bin/env python3
"""Render a script Markdown file as a self-contained, responsive HTML reading copy.

Supported subset: headings, paragraphs, unordered lists, pipe tables, bold, inline
code and links. Raw HTML is escaped. Shot tables become numbered scene cards.
Markdown remains the source of truth; no script text is invented or summarized.
"""

import argparse
from html import escape
from pathlib import Path
import re


CSS = """
:root{--paper:#f6f4ef;--white:#fffefa;--ink:#20364c;--muted:#65717a;--line:#dcdedb;--blue:#244d73;--orange:#bc522f;--wash:#eef2f4}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:30px}body{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;font-size:15px;line-height:1.85}a{color:var(--blue);text-underline-offset:4px}button{font:inherit;cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid #d98752;outline-offset:5px}::selection{background:#d8e4ed}
.layout{display:grid;grid-template-columns:248px minmax(0,1fr);max-width:1600px;margin:0 auto;min-height:100vh}.rail{padding:44px 26px;border-right:1px solid var(--line);position:sticky;top:0;height:100vh;display:flex;flex-direction:column;gap:30px}.wordmark{font-size:13px;letter-spacing:.13em;font-weight:700}.wordmark span{display:block;font-size:10px;letter-spacing:.2em;color:var(--muted);margin-top:4px}.rail-label,.eyebrow,.small-label{font-size:10px;letter-spacing:.17em;text-transform:uppercase;color:var(--muted);font-weight:650}.rail nav{display:flex;flex-direction:column;gap:6px;margin-top:12px}.rail nav a{font-size:13px;line-height:1.6;padding:9px 11px;color:var(--muted);text-decoration:none;border-left:2px solid transparent}.rail nav a:hover,.rail nav a.active{color:var(--blue);background:#e9edf0;border-left-color:var(--blue)}.rail-footer{margin-top:auto;font-size:11px;line-height:1.7;color:var(--muted)}.status-dot{display:inline-block;background:var(--orange);border-radius:50%;height:6px;width:6px;margin-right:7px}
main{min-width:0;max-width:1120px;width:100%;padding:45px 60px 72px}.toolbar{display:flex;gap:12px;justify-content:space-between;align-items:center;margin-bottom:56px}.document-label{font-size:10px;letter-spacing:.15em;color:var(--muted)}.controls{display:flex;gap:8px}.controls button{border:1px solid #cbd1d4;background:transparent;padding:6px 12px;border-radius:5px;font-size:11px;color:var(--ink)}.controls button:hover{background:#e7ecee}.hero{border-bottom:1px solid var(--line);padding-bottom:32px;margin-bottom:36px;position:relative}.eyebrow{color:var(--orange);margin-bottom:14px}.hero h1{font-family:"Songti SC","STSong",serif;font-weight:600;font-size:clamp(30px,3.7vw,49px);letter-spacing:-.035em;line-height:1.35;margin:0 0 22px;overflow-wrap:anywhere}.chips{display:flex;gap:8px;flex-wrap:wrap}.chip{padding:4px 10px;border:1px solid var(--line);border-radius:4px;font-size:11px;background:var(--white);color:var(--muted)}.chip:last-child{color:var(--orange);background:#fcf0e8;border-color:#e5c5b4}.overview{display:flex;gap:22px;margin-top:24px;align-items:center}.overview strong{font-family:Georgia,serif;font-size:37px;font-weight:400;line-height:1}.overview small{font-size:11px;color:var(--muted);display:block}.overview-copy{border-left:1px solid var(--line);padding-left:22px;font-size:12px;color:var(--muted)}
.section{margin:0 0 42px;scroll-margin-top:24px}.section-heading{display:flex;align-items:baseline;gap:12px;margin-bottom:18px}.section-number{color:var(--orange);font-family:Georgia,serif;font-size:16px}.section h2{font-size:20px;letter-spacing:-.02em;font-weight:600;margin:0}.section h3{font-size:16px;margin:24px 0 10px}.section h4{font-size:14px;margin:18px 0 8px}.section p{margin:12px 0;font-size:14px;overflow-wrap:anywhere}.section ul{padding-left:20px;margin:10px 0}.section li{margin:10px 0;font-size:13px;overflow-wrap:anywhere}.section li::marker{color:#8293a1}.section code{font-size:.92em;background:#e8edf0;border-radius:3px;padding:2px 5px;word-break:break-word}.section strong{font-weight:650}
.section.brief{background:var(--white);border:1px solid var(--line);border-radius:8px;padding:25px 28px}.brief ul{list-style:none;display:grid;grid-template-columns:1fr 1fr;gap:0 24px;padding:0;margin-bottom:0}.brief li{margin:0;padding:13px 0;border-top:1px solid #e6e7e2}.section.notes{border-left:2px solid #d4bba7;padding-left:24px}.section.notes .section-number{color:var(--orange)}
.scenes{display:grid;grid-template-columns:1fr;gap:18px}.scene{background:var(--white);border:1px solid var(--line);border-radius:8px;overflow:hidden;break-inside:avoid;box-shadow:0 3px 12px #20364c04}.scene-top{display:flex;align-items:center;gap:12px;background:var(--wash);padding:13px 22px;border-bottom:1px solid var(--line)}.scene-num{font-size:11px;letter-spacing:.14em;font-weight:650;color:var(--blue)}.scene-time{margin-left:auto;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}.scene-body{display:grid;grid-template-columns:1.1fr 1fr}.field{padding:19px 22px;min-width:0}.field+.field{border-left:1px solid #e6e7e2}.field .small-label{font-size:10px;letter-spacing:.08em;color:#75838d}.field p{font-size:13px;margin:8px 0 0;line-height:1.85}.field.dialogue{background:#fcfbf7}.dialogue p{font-size:16px;line-height:1.9;font-weight:500;color:#1f405e}.scene-note{padding:12px 22px;border-top:1px dashed var(--line);font-size:12px;color:var(--muted);display:flex;gap:14px}.scene-note .small-label{flex-shrink:0;font-size:10px;padding-top:2px}.scene-note div{min-width:0;overflow-wrap:anywhere}.scene.reveal{border-color:#ba8866}.scene.reveal .scene-top{background:#f8ece2}.scene.reveal .scene-num{color:var(--orange)}
.table-scroll{overflow:auto;border:1px solid var(--line);border-radius:7px;background:var(--white)}table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{background:var(--wash);font-weight:600}td{min-width:100px}tr:last-child td{border-bottom:0}.footer{border-top:1px solid var(--line);padding-top:20px;font-size:11px;color:var(--muted);display:flex;justify-content:space-between;gap:15px}.focus .section:not(.shot-section){display:none}.focus .hero{margin-bottom:28px}.focus .rail nav a:not([data-shots]){display:none}
@media(min-width:1400px){main{padding-left:72px;padding-right:72px}}
@media(max-width:1050px){.layout{grid-template-columns:205px minmax(0,1fr)}.rail{padding:30px 18px}main{padding:30px 30px 50px}.brief ul{grid-template-columns:1fr}.toolbar{margin-bottom:36px}}
@media(max-width:720px){body{font-size:14px}.layout{display:block}.rail{position:relative;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:18px 20px;display:block}.wordmark{font-size:11px}.wordmark span{display:none}.rail-label,.rail-footer{display:none}.rail nav{flex-direction:row;overflow:auto;gap:4px;margin-top:12px;padding-bottom:2px}.rail nav a{white-space:nowrap;padding:6px 9px;border-left:0;border-bottom:2px solid transparent;font-size:11px}.rail nav a.active{border-bottom-color:var(--blue)}main{padding:22px 18px 38px}.toolbar{margin-bottom:28px;gap:8px}.document-label{font-size:9px;letter-spacing:.08em}.controls{gap:5px}.controls button{padding:5px 8px;font-size:10px}.hero h1{font-size:32px}.hero{padding-bottom:25px}.chip{font-size:10px}.overview{gap:15px}.overview-copy{padding-left:15px}.section{margin-bottom:30px}.section h2{font-size:18px}.section.brief{padding:20px}.scene-body{grid-template-columns:1fr}.field{padding:16px 18px}.field+.field{border-left:0;border-top:1px solid #e6e7e2}.scene-top,.scene-note{padding-left:18px;padding-right:18px}.scene-note{display:block}.scene-note .small-label{margin-bottom:5px;display:block}.footer{display:block}.footer span{display:block;margin-bottom:5px}}
@page{size:A4;margin:16mm 14mm}
@media print{body{background:white;color:#162e42;font-size:11px}.layout{display:block;max-width:none}.rail,.toolbar,.footer{display:none}main{padding:0;max-width:none}.hero{padding-bottom:18px;margin-bottom:22px}.hero h1{font-size:30px}.eyebrow{margin-bottom:10px}.chip{font-size:9px}.overview strong{font-size:24px}.section{margin-bottom:24px}.section-heading{break-after:avoid}.section h2{font-size:17px}.section.brief{padding:16px 20px}.brief ul{grid-template-columns:1fr 1fr}.section p,.section li{font-size:10px}.scene{box-shadow:none;margin-bottom:12px}.scene-top{padding:9px 14px}.field{padding:12px 14px}.field p{font-size:10px}.dialogue p{font-size:12px}.scene-note{padding:8px 14px;font-size:9px}.scenes{display:block}.focus .section:not(.shot-section){display:block}.table-scroll{overflow:visible}a{color:inherit;text-decoration:none}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def inline(value):
    value = escape(value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)

    def link(match):
        label, url = match.groups()
        if re.match(r"(?i)^(javascript|data|vbscript):", url):
            return label
        return f'<a href="{url}" rel="noreferrer">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, value)


def cells(line):
    return [value.strip().replace(r"\|", "|")
            for value in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def table(headers, rows, scene_offset=0):
    shot = len(headers) >= 3 and "镜" in headers[0] and any("画面" in h for h in headers)
    if not shot:
        head = "".join(f"<th>{inline(h)}</th>" for h in headers)
        body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>" for row in rows)
        return f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>', 0
    visual = next(i for i, h in enumerate(headers) if "画面" in h)
    dialogue = next((i for i, h in enumerate(headers) if "对白" in h or "口播" in h or "台词" in h), None)
    cards = []
    for n, row in enumerate(rows, scene_offset + 1):
        if len(row) != len(headers):
            raise ValueError(f"分镜表第{n}行列数与表头不一致")
        fields = [f'<div class="field"><span class="small-label">画面与动作</span><p>{inline(row[visual])}</p></div>']
        if dialogue is not None:
            fields.append(f'<div class="field dialogue"><span class="small-label">对白 / VOICE</span><p>{inline(row[dialogue])}</p></div>')
        extra = []
        for i, header in enumerate(headers):
            if i in {0, visual, dialogue}:
                continue
            extra.append(f'<div class="scene-note"><span class="small-label">{inline(header)}</span><div>{inline(row[i])}</div></div>')
        cards.append(f'<article class="scene" id="scene-{n}"><div class="scene-top"><span class="scene-num">SHOT {n:02d}</span><span class="scene-time">{inline(row[0])}</span></div><div class="scene-body">{"".join(fields)}</div>{"".join(extra)}</article>')
    return '<div class="scenes">' + "".join(cards) + '</div>', len(rows)


def block(lines, offset):
    output, count, i = [], 0, 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.fullmatch(r"[\s|:\-]+", lines[i + 1]):
            headers, rows = cells(line), []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            rendered, added = table(headers, rows, offset + count)
            output.append(rendered)
            count += added
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append("<li>" + inline(lines[i].strip()[2:]) + "</li>")
                i += 1
            output.append("<ul>" + "".join(items) + "</ul>")
        elif re.match(r"^#{3,6} ", line):
            match = re.match(r"^(#{3,6}) (.*)", line)
            level = min(len(match[1]), 4)
            output.append(f"<h{level}>{inline(match[2])}</h{level}>")
            i += 1
        else:
            paragraph = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{2,6} |\- |\|)", lines[i].strip()):
                paragraph.append(lines[i].strip())
                i += 1
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
    return "\n".join(output), count


def render(markdown):
    lines = markdown.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("Markdown首行必须是#标题")
    title = lines.pop(0)[2:].strip()
    preamble, sections, current, heading = [], [], [], None
    for line in lines:
        if line.startswith("## "):
            if heading is not None:
                sections.append((heading, current))
            else:
                preamble = current
            heading, current = line[3:].strip(), []
        else:
            current.append(line)
    if heading is not None:
        sections.append((heading, current))
    else:
        preamble = current
    metadata = " ".join(s.strip() for s in preamble if s.strip())
    chips = "".join(f'<span class="chip">{inline(s.strip())}</span>' for s in metadata.split("｜") if s.strip())
    content, nav, scene_count = [], [], 0
    for index, (heading, source) in enumerate(sections, 1):
        body, added = block(source, scene_count)
        scene_count += added
        classes = "section"
        if added:
            classes += " shot-section"
        elif "依据" in heading or "策划" in heading:
            classes += " brief"
        elif "核实" in heading or "自查" in heading or "验证" in heading:
            classes += " notes"
        nav.append(f'<a href="#section-{index}" {"data-shots" if added else ""}>{inline(heading)}</a>')
        content.append(f'<section class="{classes}" id="section-{index}"><div class="section-heading"><span class="section-number">{index:02d}</span><h2>{inline(heading)}</h2></div>{body}</section>')
    overview = f'<div class="overview"><div><strong>{scene_count:02d}</strong><small>分镜 / SHOTS</small></div><div class="overview-copy">从创意到现场<br>动作、对白与执行说明分层阅读</div></div>' if scene_count else ''
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>{escape(title)} · 分镜脚本</title><style>{CSS}</style></head>
<body><div class="layout"><aside class="rail"><div class="wordmark">片场手记<span>ECOMMERCE / SCRIPT</span></div><div><div class="rail-label">本稿目录 / CONTENTS</div><nav aria-label="脚本目录">{"".join(nav)}</nav></div><div class="rail-footer"><span class="status-dot"></span>以文首稿件状态为准<br>创作说明 · 分镜 · 执行<br>完整内容来自同版 Markdown</div></aside>
<main><div class="toolbar"><span class="document-label">SCRIPT READING COPY / 阅读与拍摄用稿</span><div class="controls"><button id="focus-button" type="button" aria-pressed="false">只看分镜</button><button type="button" onclick="window.print()">打印 / PDF</button></div></div><header class="hero"><div class="eyebrow">CREATIVE DIRECTION · 创意编导</div><h1>{inline(title)}</h1><div class="chips">{chips}</div>{overview}</header>{"".join(content)}<footer class="footer"><span>片场手记 / 电商短视频脚本</span><span>与 Markdown 同源 · 可离线阅读 · 支持打印</span></footer></main></div>
<script>const focusButton=document.querySelector('#focus-button');focusButton.addEventListener('click',()=>{{const focused=document.body.classList.toggle('focus');focusButton.setAttribute('aria-pressed',String(focused));focusButton.textContent=focused?'查看完整稿':'只看分镜';}});const observer=new IntersectionObserver(entries=>{{for(const entry of entries){{if(entry.isIntersecting){{document.querySelectorAll('nav a').forEach(link=>link.classList.toggle('active',link.hash==='#'+entry.target.id));}}}}}},{{rootMargin:'-5% 0px -65% 0px'}});document.querySelectorAll('main section').forEach(section=>observer.observe(section));</script></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="同版Markdown脚本")
    parser.add_argument("--output", type=Path, help="默认使用同名.html")
    parser.add_argument("--overwrite", action="store_true", help="确认重新生成已存在的HTML")
    args = parser.parse_args()
    output = args.output or args.source.with_suffix(".html")
    if output.resolve() == args.source.resolve():
        parser.error("不能覆盖Markdown源文件")
    if output.exists() and not args.overwrite:
        parser.error("HTML已存在；确认源文件版本后使用--overwrite或选择新文件名")
    result = render(args.source.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding="utf-8")
    print(output.resolve())


if __name__ == "__main__":
    main()
