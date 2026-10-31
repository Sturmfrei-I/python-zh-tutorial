#!/usr/bin/env python3
"""把 content/<大类>/*.md 和 src/ 生成静态网站，只依赖标准库。

    python3 build.py
    SITE_URL=https://example.com/ python3 build.py   # 上线时指定正式域名

产物：
    dist/                     部署到静态托管的完整网站，每章一个独立页面
    preview/artifact.html     全站合并成的单文件预览版，用于发布为 Claude Artifact
"""
from __future__ import annotations

import datetime
import hashlib
import html
import json
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from render import Renderer

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
SRC = ROOT / "src"
DIST = ROOT / "dist"
PREVIEW = ROOT / "preview"

SITE_NAME = "Python 与 AI 开发教程"
SEO_TITLE = "Python 中文教程：AI 开发、Agent 开发和大模型开发入门"
SEO_ALTERNATE_NAME = "Python 中文教程"
SITE_LEDE = (
    "写给有编程经验的开发者的 AI Agent 应用开发教程。从 Python 语言学起，"
    "一步步掌握服务端、大模型和 Agent 开发，重要概念都和你熟悉的语言对比。"
)
SEO_DESCRIPTION = (
    "写给有编程经验的开发者的 AI 开发教程。从 Python 入门学起，一步步掌握 FastAPI 后端、"
    "大模型开发、AI Agent 智能体开发、RAG 和 MCP，重要概念都和 Java、Kotlin 对比。"
)
SHEET_ID = "cheatsheet"
SHEET_TITLE = "Python 语法速查表：和 Java、Kotlin 写法对照"
SHEET_DESCRIPTION = "汇总 Python 常用语法、内置函数、容器操作和标准库模块，并列出 Java、Kotlin 的对应写法，写代码时随手查。"
SEO_KEYWORDS = (
    "Python 中文教程,Python 教程,Python 入门,AI 开发,AI 开发教程,AI 应用开发,Agent 开发,AI Agent 开发,智能体开发,"
    "大模型开发,大模型应用开发,LLM 应用开发,RAG 教程,MCP 教程,LangGraph 教程,FastAPI 教程,Java 转 AI,Java 转 Python,Kotlin 转 Python"
)
# 搜索结果里的标题大约显示 30 个汉字，超过这个宽度时构建会提示
TITLE_WIDTH = 60
# Google Search Console 的所有权验证码，Google 在首页检查，验证通过后也不能删
GOOGLE_VERIFICATION = "ZOPwlI-WvfsT5csCNK3b1XqO9NLzmYUFdc1YnqqCNFs"
# 正式域名，比如 https://example.com/。设置后才会生成 canonical、og:url 和 sitemap.xml
SITE_URL = os.environ.get("SITE_URL", "")
if SITE_URL and not SITE_URL.endswith("/"):
    SITE_URL += "/"
RESERVED_IDS = {"main", "bar", "side", "spot", "scrim", "progress", "pager"}
RESERVED_PAGES = {"functions", "assets", "home", SHEET_ID}  # Cloudflare Pages 部署时会忽略 functions 目录，其余已被本站占用
HLJS = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
PYTHON_TUTORIAL = "https://docs.python.org/zh-cn/3.12/tutorial/"

FENCE = re.compile(r"^```(\S*)\s*(.*)$")
CONTAINER = re.compile(r"^:::(\w+)\s*(.*?)\s*(?:\{#([\w-]+)\})?\s*$")
HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*(?:\{#([\w-]+)\})?\s*$")
BULLET = re.compile(r"^(?:-|\d+\.)\s+(.*)$")


def fail(where: str, message: str) -> None:
    sys.exit(f"[{where}] {message}")


def load_languages() -> list[dict]:
    return json.loads((ROOT / "languages.json").read_text("utf-8"))["languages"]


def load_categories() -> list[dict]:
    return json.loads((ROOT / "categories.json").read_text("utf-8"))["categories"]


LANGUAGES = load_languages()
LANGUAGE_IDS = [lang["id"] for lang in LANGUAGES]
BASE = LANGUAGE_IDS[0]
CATEGORIES = load_categories()
RESERVED_PAGES.update(category["id"] for category in CATEGORIES)  # 大类页面用的网址


# ---------- 行内语法：`code`、**粗体**、[链接](url) ----------

def inline(text: str) -> str:
    out = []
    for part in re.split(r"(`[^`]+`)", text):
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            out.append(f"<code>{html.escape(part[1:-1], quote=False)}</code>")
            continue
        escaped = html.escape(part, quote=False)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(
            r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
            r'<a href="\2" target="_blank" rel="noopener">\1</a>',
            escaped,
        )
        out.append(escaped)
    return "".join(out)


# ---------- 块级语法 ----------

def split_row(line: str) -> list[str]:
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [cell.strip().replace(r"\|", "|") for cell in cells]


def find_close(lines: list[str], start: int, where: str) -> int:
    depth, fenced = 1, False
    for i in range(start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            fenced = not fenced
        elif fenced:
            continue
        elif stripped == ":::":
            depth -= 1
            if depth == 0:
                return i
        elif stripped.startswith(":::"):
            depth += 1
    fail(where, "容器缺少结束标记 :::")


def read_code(lines: list[str], start: int, match: re.Match, blocks: list, where: str) -> int:
    info, flags = match.groups()
    end = start + 1
    while end < len(lines) and not lines[end].startswith("```"):
        end += 1
    body = lines[start + 1 : end]

    if info == "output":
        if not blocks or blocks[-1]["type"] != "code":
            fail(where, "output 块前面必须是代码块")
        blocks[-1]["output"] = "\n".join(body)
        return end + 1

    # ```java:xml 表示放在 Java 一栏，但按 XML 高亮
    col, _, hl = info.partition(":")
    hl = hl or col
    # 以 § 开头的行不展示，只在 tools/verify.py 运行时使用
    src = "\n".join(l[2:] if l.startswith("§ ") else l for l in body)
    code = "\n".join(l for l in body if not l.startswith("§"))
    blocks.append({
        "type": "code",
        "col": col,
        "hl": hl,
        "code": code,
        "src": src,
        "run": col == hl and col in LANGUAGE_IDS and "no-run" not in flags,
    })
    return end + 1


def make_diff_table(title: str, lines: list[str], where: str) -> dict:
    """异同表：首列是对比项，其余列名是语言 id，单元格写 = 表示和基准语言相同。"""
    head = split_row(lines[0])
    langs = head[1:]
    unknown = [lang for lang in langs if lang not in LANGUAGE_IDS]
    if unknown:
        fail(where, f"对比块「{title}」的异同表里有未注册的语言 {unknown}")
    rows = []
    for line in lines[2:]:
        cells = split_row(line)
        if len(cells) != len(head):
            fail(where, f"对比块「{title}」的异同表列数不对：{line}")
        row = {"label": inline(cells[0])}
        row.update({lang: inline(cell) for lang, cell in zip(langs, cells[1:])})
        rows.append(row)
    return {"cols": langs, "rows": rows}


def make_compare(title: str, anchor: str | None, inner: list[str], where: str) -> dict:
    cols, notes, take, intro, table = {}, {}, None, [], None
    for block in parse_blocks(inner, where):
        if block["type"] == "code":
            cols[block["col"]] = block
        elif block["type"] == "table":
            table = make_diff_table(title, block["lines"], where)
        elif block["type"] == "quote":
            for line in block["lines"]:
                key, _, value = line.partition(":")
                key = key.strip()
                if key == "要点":
                    take = inline(value.strip())
                elif key in LANGUAGE_IDS:
                    notes[key] = inline(value.strip())
                else:
                    fail(where, f"对比块「{title}」里的注解键 {key!r} 未注册")
        elif block["type"] == "p":
            intro.append(block["html"])
        else:
            fail(where, f"对比块「{title}」里不支持 {block['type']}")
    if BASE not in cols:
        fail(where, f"对比块「{title}」缺少 {BASE} 代码")
    return {"type": "compare", "title": inline(title), "anchor": anchor, "intro": intro,
            "cols": cols, "table": table, "notes": notes, "take": take}


def make_map(title: str, inner: list[str], where: str) -> dict:
    rows = [split_row(line) for line in inner if line.strip().startswith("|")]
    if len(rows) < 3:
        fail(where, f"对照表「{title}」至少需要表头、分隔线和一行数据")
    head, body = rows[0], rows[2:]
    return {"type": "map", "title": inline(title), "cols": head,
            "rows": [{key: inline(cell) for key, cell in zip(head, row)} for row in body]}


def make_container(kind: str, title: str, anchor: str | None, inner: list[str], where: str) -> dict:
    if kind == "compare":
        return make_compare(title, anchor, inner, where)
    if kind == "map":
        return make_map(title, inner, where)
    if kind == "recap":
        return {"type": "recap", "items": [inline(m.group(1)) for m in map(BULLET.match, inner) if m]}
    if kind in ("tip", "warn", "more"):
        return {"type": kind, "title": inline(title), "blocks": parse_blocks(inner, where)}
    fail(where, f"未知容器 :::{kind}")


def parse_blocks(lines: list[str], where: str) -> list[dict]:
    blocks: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
        elif match := FENCE.match(line):
            i = read_code(lines, i, match, blocks, where)
        elif match := CONTAINER.match(stripped):
            kind, title, anchor = match.groups()
            end = find_close(lines, i + 1, where)
            blocks.append(make_container(kind, title, anchor, lines[i + 1 : end], where))
            i = end + 1
        elif stripped.startswith("### "):
            blocks.append({"type": "h3", "html": inline(stripped[4:])})
            i += 1
        elif stripped.startswith("|"):
            table = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table.append(lines[i])
                i += 1
            blocks.append({"type": "table", "lines": table})
        elif stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append({"type": "quote", "lines": quote})
        elif BULLET.match(stripped):
            ordered = stripped[0].isdigit()
            items = []
            while i < len(lines) and (match := BULLET.match(lines[i].strip())):
                items.append(inline(match.group(1)))
                i += 1
            blocks.append({"type": "list", "ordered": ordered, "items": items})
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(```|:::|>|\||###\s|-\s|\d+\.\s)", lines[i].strip()):
                para.append(lines[i].strip())
                i += 1
            blocks.append({"type": "p", "html": inline("".join(para))})
    return blocks


def split_sections(lines: list[str]) -> list[tuple[re.Match | None, list[str]]]:
    parts: list[tuple[re.Match | None, list[str]]] = [(None, [])]
    fenced = False
    for line in lines:
        if line.startswith("```"):
            fenced = not fenced
        match = None if fenced else HEADING.match(line)
        if match and len(match.group(1)) == 2:
            parts.append((match, []))
        else:
            parts[-1][1].append(line)
    return parts


def walk(blocks: list[dict]):
    for block in blocks:
        yield block
        if "blocks" in block:
            yield from walk(block["blocks"])


def source_url(target: str) -> str:
    """完整网址原样使用，其余按 Python 官方教程里的页面名处理。"""
    target = target.strip()
    return target if target.startswith("https://") else PYTHON_TUTORIAL + target


def parse_chapter(path: Path) -> dict:
    where = path.name
    text = path.read_text("utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        fail(where, "缺少 front matter")
    meta = dict(line.split(": ", 1) for line in match.group(1).splitlines())
    if meta["id"] in RESERVED_PAGES:
        fail(where, f"章节 id {meta['id']!r} 是保留名，会导致页面丢失或冲突，请换一个")

    intro_lines, sections = [], []
    for heading, lines in split_sections(match.group(2).splitlines()):
        if heading is None:
            intro_lines = lines
            continue
        title, anchor = heading.group(2), heading.group(3)
        if not anchor:
            fail(where, f"小节「{title}」缺少 {{#id}}")
        if anchor in RESERVED_IDS:
            fail(where, f"小节 id {anchor!r} 和页面元素冲突，请换一个")
        sections.append({"id": anchor, "title": inline(title), "blocks": parse_blocks(lines, where)})

    chapter = {
        "id": meta["id"],
        "part": meta["part"],
        "title": meta["title"],
        "lede": inline(meta["lede"]),
        "seo_title": meta["seo_title"],
        "seo_description": meta["seo_description"],
        "updated": datetime.date.fromtimestamp(path.stat().st_mtime).isoformat(),
        "sources": [
            {"title": name.strip(), "url": source_url(target)}
            for name, target in (item.split("|") for item in meta["source"].split(";"))
        ],
        "versions": meta.get("versions", ""),
        "intro": parse_blocks(intro_lines, where),
        "sections": sections,
        "recap": [],
    }

    # 章末要点从正文里摘出来单独渲染
    for section in sections:
        for block in section["blocks"]:
            if block["type"] == "recap":
                chapter["recap"] = block["items"]
        section["blocks"] = [b for b in section["blocks"] if b["type"] != "recap"]

    count, chars, code_lines = 0, 0, 0
    everything = chapter["intro"] + [b for s in sections for b in s["blocks"]]
    for block in walk(everything):
        if block["type"] == "compare":
            count += 1
            block["id"] = f"vs{count}"
            code_lines += sum(c["code"].count("\n") + 1 for c in block["cols"].values())
            chars += len(block["take"] or "") + sum(len(n) for n in block["notes"].values())
            if block["table"]:
                chars += sum(len(cell) for row in block["table"]["rows"] for cell in row.values())
        elif block["type"] == "code":
            code_lines += block["code"].count("\n") + 1
        elif block["type"] in ("p", "h3"):
            chars += len(block["html"])
        elif block["type"] == "list":
            chars += sum(len(item) for item in block["items"])
    chapter["compares"] = count
    chapter["minutes"] = max(5, round(chars / 420 + code_lines / 18))
    return chapter


def load_course() -> dict:
    known = {category["id"] for category in CATEGORIES}
    stray = [p.name for p in CONTENT.iterdir() if p.suffix == ".md" or (p.is_dir() and p.name not in known)]
    if stray:
        fail("content", f"这些内容不在 categories.json 注册的大类目录里：{', '.join(sorted(stray))}")

    categories = []
    for category in CATEGORIES:
        chapters = [parse_chapter(p) for p in sorted((CONTENT / category["id"]).glob("*.md"))]
        if not chapters:  # 还没写内容的大类不显示
            continue
        for number, chapter in enumerate(chapters, 1):
            chapter["no"] = number
            chapter["category"] = category["id"]
            for block in walk(chapter["intro"] + [b for s in chapter["sections"] for b in s["blocks"]]):
                if block["type"] == "compare":
                    block["stacked"] = category.get("stacked", False)
        parts = list(dict.fromkeys(ch["part"] for ch in chapters))
        categories.append({**category, "parts": parts, "chapters": chapters})

    chapters = [chapter for category in categories for chapter in category["chapters"]]
    ids = [chapter["id"] for chapter in chapters]
    repeated = sorted({page for page in ids if ids.count(page) > 1})
    if repeated:
        fail("content", f"章节 id 重复，所有大类共用一层网址：{', '.join(repeated)}")
    return {"title": SITE_NAME, "languages": LANGUAGES, "categories": categories, "chapters": chapters}


def coverage(chapters: list[dict]) -> dict[str, tuple[int, int]]:
    """每门语言分别有多少组对比写了代码、写了异同表。"""
    code = {lang: 0 for lang in LANGUAGE_IDS}
    table = {lang: 0 for lang in LANGUAGE_IDS}
    for chapter in chapters:
        for block in walk(chapter["intro"] + [b for s in chapter["sections"] for b in s["blocks"]]):
            if block["type"] == "compare":
                for lang in block["cols"]:
                    code[lang] += 1
                for lang in block["table"]["cols"] if block["table"] else []:
                    table[lang] += 1
    return {lang: (code[lang], table[lang]) for lang in LANGUAGE_IDS}


def json_ld(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def language_css() -> str:
    """语言色来自 languages.json。对比卡片的 color-scheme 是 dark，会自动取亮色版本。"""
    return "\n".join(
        f'[data-lang="{lang["id"]}"],[data-col="{lang["id"]}"]'
        f'{{--c:light-dark({lang["color"]},{lang["colorOnDark"]})}}'
        for lang in LANGUAGES
    )


def page_path(page_id: str) -> str:
    return "" if page_id == "home" else f"{page_id}/"


def page_list(course: dict) -> list[dict]:
    chapters = course["chapters"]
    category_names = {category["id"]: category["name"] for category in course["categories"]}
    sheet_category = next(category for category in course["categories"] if category.get("cheatsheet"))
    pages = [{
        "id": "home",
        "view": "home",
        "title": SEO_TITLE,
        "name": SITE_NAME,
        "description": SEO_DESCRIPTION,
        "updated": max(ch["updated"] for ch in chapters),
        "schema": {
            "@context": "https://schema.org",
            "@type": "Course",
            "name": SITE_NAME,
            "description": SEO_DESCRIPTION,
            "inLanguage": "zh-CN",
            "teaches": ["Python", "AI 开发", "大模型开发", "AI Agent 开发"],
            "syllabusSections": [
                {"@type": "Syllabus", "name": ch["title"], "description": ch["seo_description"]}
                for ch in chapters
            ],
        },
    }]
    for category in course["categories"]:
        pages.append({
            "id": category["id"],
            "view": "category",
            "category": category,
            "title": category["seo_title"],
            "name": f'{category["name"]} | {SITE_NAME}',
            "description": category["seo_description"],
            "updated": max(ch["updated"] for ch in category["chapters"]),
            "trail": [(SITE_NAME, "home"), (category["name"], category["id"])],
            "schema": {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": category["seo_title"],
                "description": category["seo_description"],
                "inLanguage": "zh-CN",
                "isPartOf": {"@type": "Course", "name": SITE_NAME},
            },
        })
    for chapter in chapters:
        pages.append({
            "id": chapter["id"],
            "view": "chapter",
            "chapter": chapter,
            "title": chapter["seo_title"],
            "name": f'{chapter["title"]} | {SITE_NAME}',
            "description": chapter["seo_description"],
            "updated": chapter["updated"],
            "trail": [
                (SITE_NAME, "home"),
                (category_names[chapter["category"]], chapter["category"]),
                (chapter["title"], chapter["id"]),
            ],
            "schema": {
                "@context": "https://schema.org",
                "@type": "TechArticle",
                "headline": chapter["seo_title"],
                "description": chapter["seo_description"],
                "inLanguage": "zh-CN",
                "dateModified": chapter["updated"],
                "isPartOf": {"@type": "Course", "name": SITE_NAME},
            },
        })
    pages.append({
        "id": SHEET_ID,
        "view": "sheet",
        "title": SHEET_TITLE,
        "name": f"速查表 | {SITE_NAME}",
        "description": SHEET_DESCRIPTION,
        "updated": max(ch["updated"] for ch in chapters),
        "trail": [(SITE_NAME, "home"), (sheet_category["name"], sheet_category["id"]), ("速查表", SHEET_ID)],
        "schema": {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": SHEET_TITLE,
            "description": SHEET_DESCRIPTION,
            "inLanguage": "zh-CN",
            "isPartOf": {"@type": "Course", "name": SITE_NAME},
        },
    })
    return pages


def website_schema() -> dict:
    """首页的站点信息。章节标题不再带站名，Google 用它在搜索结果里显示站名。"""
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "alternateName": SEO_ALTERNATE_NAME,
        "url": SITE_URL,
        "inLanguage": "zh-CN",
    }


def breadcrumb_schema(trail: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": position, "name": name, "item": SITE_URL + page_path(page_id)}
            for position, (name, page_id) in enumerate(trail, start=1)
        ],
    }


def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in text)


def head_tags(page: dict, root: str, version: str) -> str:
    title = html.escape(page["title"], quote=True)
    description = html.escape(page["description"], quote=True)
    tags = [
        f"<title>{title}</title>",
        f'<meta name="description" content="{description}">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        f'<meta property="og:type" content="{"article" if page["view"] in ("chapter", "sheet") else "website"}">',
        '<meta property="og:locale" content="zh_CN">',
        f'<link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml">',
        f'<link rel="stylesheet" href="{root}assets/app.css?v={version}">',
    ]
    if page["view"] == "home":
        tags.insert(2, f'<meta name="keywords" content="{SEO_KEYWORDS}">')
        tags.insert(3, f'<meta name="google-site-verification" content="{GOOGLE_VERIFICATION}">')
    if SITE_URL:
        url = SITE_URL + page_path(page["id"])
        tags += [f'<link rel="canonical" href="{url}">', f'<meta property="og:url" content="{url}">']
    if page.get("schema"):
        schema = dict(page["schema"])
        if SITE_URL:
            schema["url"] = SITE_URL + page_path(page["id"])
        tags.append(f'<script type="application/ld+json">{json_ld(schema)}</script>')
    if SITE_URL and page["view"] == "home":
        tags.append(f'<script type="application/ld+json">{json_ld(website_schema())}</script>')
    if SITE_URL and page.get("trail"):
        tags.append(f'<script type="application/ld+json">{json_ld(breadcrumb_schema(page["trail"]))}</script>')
    return "\n".join(tags)


# 在首次绘制之前恢复主题，避免跳转页面时闪一下
THEME_BOOT = (
    "<script>try{var d=document.documentElement,s=localStorage,t=JSON.parse(s.getItem('pyvs.theme'));"
    "if(t&&t!='auto')d.dataset.theme=t;if(JSON.parse(s.getItem('pyvs.side'))=='closed')d.dataset.side='closed'}"
    "catch(e){}"
    # 跨页过渡被浏览器跳过时不算错误，比如页面在后台
    "function q(e){var v=e.viewTransition,n=function(){};if(v){v.ready.catch(n);v.finished.catch(n);v.updateCallbackDone.catch(n)}}"
    "addEventListener('pagereveal',q);addEventListener('pageswap',q)</script>"
)


def static_page(page: dict, body: str, root: str, version: str, extra_head: str = "") -> str:
    return (
        f'<!doctype html>\n<html lang="zh-CN" data-view="{page["view"]}" data-page="{page["id"]}">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"{head_tags(page, root, version)}\n{extra_head}{THEME_BOOT}\n</head>\n<body>\n{body}\n"
        f'<script src="{HLJS}" defer></script>\n'
        f'<script src="{root}assets/app.js?v={version}"></script>\n</body>\n</html>\n'
    )


def write_site_files(pages: list[dict], course: dict) -> None:
    if SITE_URL:
        rows = "".join(
            f"  <url><loc>{SITE_URL}{page_path(p['id'])}</loc><lastmod>{p['updated']}</lastmod></url>\n"
            for p in pages
        )
        (DIST / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}</urlset>\n',
            "utf-8",
        )
    robots = "User-agent: *\nAllow: /\n"
    if SITE_URL:
        robots += f"\nSitemap: {SITE_URL}sitemap.xml\n"
    (DIST / "robots.txt").write_text(robots, "utf-8")

    entries = "\n".join(
        f"- [{p['title']}]({SITE_URL}{page_path(p['id'])}): {p['description']}"
        for p in pages if p["view"] != "home"
    )
    (DIST / "llms.txt").write_text(
        f"# {SITE_NAME}\n\n> {pages[0]['description']}\n\n## 章节\n\n{entries}\n", "utf-8"
    )


def main() -> None:
    course = load_course()
    site = Renderer(course, SITE_NAME, SITE_LEDE, SHEET_ID)
    pages = page_list(course)
    for page in pages:
        if display_width(page["title"]) > TITLE_WIDTH:
            print(f"标题偏长：{page['title']}")

    css = (SRC / "app.css").read_text("utf-8") + "\n" + language_css() + "\n"
    js = (SRC / "app.js").read_text("utf-8")
    search = json.dumps(site.search_index(), ensure_ascii=False, separators=(",", ":"))
    version = hashlib.sha1((css + js + search).encode("utf-8")).hexdigest()[:8]
    shell = (SRC / "shell.html").read_text("utf-8")

    shutil.rmtree(DIST, ignore_errors=True)
    (DIST / "assets").mkdir(parents=True)
    (DIST / "assets/app.css").write_text(css, "utf-8")
    (DIST / "assets/app.js").write_text(js, "utf-8")
    (DIST / "assets/search.json").write_text(search, "utf-8")
    shutil.copy(SRC / "favicon.svg", DIST / "assets/favicon.svg")

    for page in pages:
        root = "" if page["id"] == "home" else "../"
        body = site.shell(shell, page, root, site.main_html(page, root), f"assets/search.json?v={version}")
        target = DIST / page_path(page["id"]) / "index.html"
        target.parent.mkdir(exist_ok=True)
        target.write_text(static_page(page, body, root, version), "utf-8")

    base_path = urlparse(SITE_URL).path or "/"
    missing = {"id": "home", "view": "home", "title": f"页面不存在 | {SITE_NAME}",
               "description": SEO_DESCRIPTION}
    (DIST / "404.html").write_text(
        static_page(missing, site.shell(shell, missing, base_path, site.not_found_html(base_path),
                                        f"assets/search.json?v={version}"),
                    base_path, version, '<meta name="robots" content="noindex">\n'),
        "utf-8",
    )
    write_site_files(pages, course)

    # 单文件预览版：所有页面放进 <template>，由 app.js 切换
    templates = "\n".join(
        f'<template data-page="{p["id"]}" data-view="{p["view"]}" data-title="{html.escape(p["name"], quote=True)}">'
        f'{site.main_html(p, "")}</template>'
        for p in pages
    )
    PREVIEW.mkdir(exist_ok=True)
    (PREVIEW / "artifact.html").write_text(
        f'<meta charset="utf-8">\n<title>{SITE_NAME}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
        f"{THEME_BOOT}\n<style>\n{css}</style>\n{site.shell(shell, pages[0], '', '', '')}\n{templates}\n"
        f'<script src="{HLJS}" defer></script>\n'
        f'<script type="application/json" id="search-data">{search.replace("<", chr(92) + "u003c")}</script>\n'
        f"<script>\n{js}\n</script>\n",
        "utf-8",
    )

    total = sum(ch["compares"] for ch in course["chapters"])
    print(f"{len(course['chapters'])} 章，{len(pages)} 个页面，{total} 组对比，约 {sum(ch['minutes'] for ch in course['chapters'])} 分钟")
    for lang, (code, table) in coverage(course["chapters"]).items():
        print(f"  {lang:<8} 代码 {code}/{total}  异同表 {table}/{total}")
    if not SITE_URL:
        print("未设置 SITE_URL：跳过 canonical 和 sitemap.xml，上线前要设置")


if __name__ == "__main__":
    main()
