"""把解析好的内容渲染成 HTML。

页面结构都在这里生成，搜索引擎不运行 JavaScript 也能读到全部正文。
src/app.js 只负责语言切换、搜索、进度这些交互。
"""
from __future__ import annotations

import html
import re

MAX_TABS = 4  # 语言不多时用分段标签，超过这个数量换成下拉选择

ICONS = {
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/>',
    "swap": '<path d="M7 4 3 8l4 4M3 8h14M17 12l4 4-4 4M21 16H7"/>',
    "check": '<path d="m5 12.5 4.6 4.6L19 7.5"/>',
    "copy": '<rect x="8.5" y="8.5" width="11.5" height="11.5" rx="2.5"/><path d="M15.5 8.5v-2A2.5 2.5 0 0 0 13 4H6.5A2.5 2.5 0 0 0 4 6.5V13a2.5 2.5 0 0 0 2.5 2.5h2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/>',
    "auto": '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17a8.5 8.5 0 0 0 0-17Z" fill="currentColor"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "chevron": '<path d="m9 6 6 6-6 6"/>',
    "bulb": '<path d="M9 18h6M10 21h4M12 3a6.5 6.5 0 0 0-3.7 11.8c.5.4.7 1 .7 1.7h6c0-.7.2-1.3.7-1.7A6.5 6.5 0 0 0 12 3Z"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "link": '<path d="M14 5h5v5M19 5l-8 8M10 5H6.5A1.5 1.5 0 0 0 5 6.5v11A1.5 1.5 0 0 0 6.5 19h11a1.5 1.5 0 0 0 1.5-1.5V14"/>',
    "table": '<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="M3.5 10h17M10 10v9"/>',
    "warn": '<path d="M12 4 2.8 19.5h18.4L12 4Z"/><path d="M12 10v4.5M12 17.2v.1"/>',
}


def icon(name: str) -> str:
    return f'<svg class="i" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def plain(markup: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", markup or ""))


def code_lines(code: str) -> str:
    """逐行包裹代码，长行折行时保持悬挂缩进。

    高亮由浏览器在加载后完成，行结构和这里相同，所以上色时页面不会跳动。
    """
    lines = code.split("\n")
    out = []
    for i, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" "))
        lead = f'<span class="ind">{" " * indent}</span>' if indent else ""
        newline = "\n" if i < len(lines) - 1 else ""
        out.append(f'<span class="ln" style="--i:{indent}">{lead}{html.escape(line[indent:], quote=False)}{newline}</span>')
    return "".join(out)


def walk(blocks: list[dict]):
    for block in blocks:
        yield block
        if "blocks" in block:
            yield from walk(block["blocks"])


def chapter_blocks(chapter: dict):
    yield from walk(chapter["intro"])
    for section in chapter["sections"]:
        yield from walk(section["blocks"])


def reading_time(category: dict) -> str:
    minutes = sum(chapter["minutes"] for chapter in category["chapters"])
    return f"约 {minutes} 分钟" if minutes < 60 else f"约 {round(minutes / 60, 1)} 小时"


class Renderer:
    def __init__(self, course: dict, site_name: str, site_lede: str, sheet_id: str):
        self.course = course
        self.site_name = site_name
        self.site_lede = site_lede
        self.sheet_id = sheet_id
        self.chapters = course["chapters"]
        self.categories = course["categories"]
        self.category_by_id = {category["id"]: category for category in self.categories}
        # 正文里写「章节名」或「大类名」时，自动链接到对应页面
        self.references = {chapter["title"]: chapter["id"] for chapter in self.chapters}
        self.references.update({category["name"]: category["id"] for category in self.categories})
        self.sheet_category = next(category for category in self.categories if category.get("cheatsheet"))
        self.languages = course["languages"]
        self.base = self.languages[0]["id"]
        self.others = [lang["id"] for lang in self.languages[1:]]
        self.by_id = {lang["id"]: lang for lang in self.languages}

    @staticmethod
    def link(root: str, page: str, frag: str = "") -> str:
        """内部链接。data-page 给单文件预览版用，正式网站里就是普通链接。"""
        href = (f"{root}{'' if page == 'home' else page + '/'}") or "./"
        if frag:
            href += f"#{frag}"
        return f'href="{href}" data-page="{page}"' + (f' data-frag="{frag}"' if frag else "")

    def link_references(self, content: str, chapter: dict, root: str) -> str:
        """把正文里的「章节名」和「第 N 章」换成站内链接，代码块不处理。"""
        siblings = self.category_by_id[chapter["category"]]["chapters"]

        def by_name(match: re.Match) -> str:
            page = self.references.get(match[1])
            if page in (None, chapter["id"]):
                return match[0]
            return f'「<a {self.link(root, page)}>{match[1]}</a>」'

        def by_number(match: re.Match) -> str:
            number = int(match[1])
            if number == chapter["no"] or not 0 < number <= len(siblings):
                return match[0]
            return f'<a {self.link(root, siblings[number - 1]["id"])}>{match[0]}</a>'

        parts = re.split(r"(<pre\b.*?</pre>)", content, flags=re.S)
        return "".join(
            part if part.startswith("<pre")
            else re.sub(r"第 (\d+) 章", by_number, re.sub(r"「([^「」<>]+)」", by_name, part))
            for part in parts
        )

    # ---------- 内容块 ----------

    def code_tag(self, code: str, hl: str) -> str:
        name = self.by_id[hl]["hljs"] if hl in self.by_id else hl
        return f'<code data-hl="{esc(name)}">{code_lines(code)}</code>'

    @staticmethod
    def copy_button() -> str:
        return f'<button class="copy" type="button" aria-label="拷贝代码">{icon("copy")}<span>拷贝</span></button>'

    def code_figure(self, block: dict) -> str:
        label = self.by_id[block["col"]]["name"] if block["col"] in self.by_id else {
            "bash": "终端", "text": "文本"}.get(block["hl"], block["hl"])
        output = ""
        if block.get("output"):
            output = f'<div class="output"><span>输出</span><pre tabindex="0">{esc(block["output"])}</pre></div>'
        return (
            f'<figure class="code"><div class="code-head"><span>{esc(label)}</span>{self.copy_button()}</div>'
            f'<pre tabindex="0">{self.code_tag(block["code"], block["hl"])}</pre>{output}</figure>'
        )

    def seg_tabs(self, ids: list[str]) -> str:
        tabs = "".join(
            f'<button type="button" role="tab" data-lang="{lang}" aria-selected="{"true" if i == 0 else "false"}"'
            f'{"" if i == 0 else " tabindex=" + chr(34) + "-1" + chr(34)}>{esc(self.by_id[lang]["name"])}</button>'
            for i, lang in enumerate(ids)
        )
        return (
            f'<div class="seg-scroll"><div class="seg" role="tablist" aria-label="选择对比语言" style="--n:{len(ids)};--i:0">'
            f'<i class="seg-thumb"></i>{tabs}</div></div>'
        )

    def lang_picker(self, ids: list[str]) -> str:
        options = "".join(f'<option value="{lang}">{esc(self.by_id[lang]["name"])}</option>' for lang in ids)
        return f'<label class="lang-pick"><span class="sr">选择对比语言</span><select>{options}</select></label>'

    def diff_table(self, block: dict, lang: str, hidden: bool) -> str:
        """异同表：单元格写 = 表示和 Python 相同，合并成一行。不同点在前，相同点在后。"""
        table = block.get("table")
        if not table or lang not in table["cols"]:
            return ""
        same = [row for row in table["rows"] if row[lang] == "="]
        diff = [row for row in table["rows"] if row[lang] != "="]
        rows = "".join(
            f'<tr><th scope="row">{row["label"]}</th><td>{row[self.base]}</td><td>{row[lang]}</td></tr>' for row in diff
        ) + "".join(
            f'<tr class="is-same"><th scope="row">{row["label"]}</th><td colspan="2">'
            f'<span class="same-tag">{icon("check")}相同</span>{row[self.base]}</td></tr>'
            for row in same
        )
        return (
            f'<table class="vs-table" data-col="{lang}"{" hidden" if hidden else ""}><thead><tr>'
            '<th scope="col"><span class="sr">对比项</span></th>'
            f'<th scope="col" data-lang="{self.base}">{esc(self.by_id[self.base]["name"])}</th>'
            f'<th scope="col" data-lang="{lang}">{esc(self.by_id[lang]["name"])}</th>'
            f"</tr></thead><tbody>{rows}</tbody></table>"
        )

    def compare_card(self, block: dict, compact: bool = False) -> str:
        ids = [lang for lang in self.others if lang in block["cols"]]
        base = block["cols"][self.base]
        panes = "".join(
            f'<pre tabindex="0" data-col="{lang}"{" hidden" if i else ""}>'
            f'{self.code_tag(block["cols"][lang]["code"], block["cols"][lang]["hl"])}</pre>'
            for i, lang in enumerate(ids)
        )
        details = ""
        if not compact:
            tables = "".join(self.diff_table(block, lang, i > 0) for i, lang in enumerate(ids))
            notes = "".join(
                f'<p class="vs-note" data-col="{lang}"{" hidden" if i else ""}>{block["notes"][lang]}</p>'
                for i, lang in enumerate(ids) if lang in block["notes"]
            )
            if tables:
                details += f'<div class="vs-diff">{tables}</div>'
            details += notes
            if block.get("take"):
                details += f'<p class="vs-take">{icon("bulb")}<span>{block["take"]}</span></p>'
        picker = self.lang_picker(ids) if len(ids) > MAX_TABS else self.seg_tabs(ids)
        intro = "".join(f'<p class="vs-intro">{text}</p>' for text in block["intro"])
        return (
            f'<section class="vs{" is-stacked" if block.get("stacked") else ""}" id="{block["id"]}" data-langs="{",".join(ids)}">'
            f'<h3 class="vs-title">{block["title"]}</h3>{intro}<div class="vs-code">'
            f'<div class="vs-pane"><div class="vs-bar"><span class="vs-lang" data-lang="{self.base}">'
            f'{esc(self.by_id[self.base]["name"])}</span>{self.copy_button()}</div>'
            f'<pre tabindex="0">{self.code_tag(base["code"], base["hl"])}</pre></div>'
            f'<div class="vs-pane vs-other"><div class="vs-bar">{picker}{self.copy_button()}</div>{panes}</div>'
            f"</div>{details}</section>"
        )

    def map_table(self, block: dict) -> str:
        cols = [key for key in block["cols"] if key in self.by_id or key == "note"]
        ids = [key for key in cols if key in self.by_id and key != self.base]
        shown = ids[:1]

        def hidden(key: str) -> str:
            return " hidden" if key in self.by_id and key != self.base and key not in shown else ""

        head = "".join(
            f'<th scope="col" data-col="{key}"{hidden(key)}>{esc(self.by_id[key]["name"])}</th>' if key in self.by_id
            else '<th scope="col">说明</th>'
            for key in cols
        )
        rows = "".join(
            "<tr>" + "".join(
                f'<td data-col="{key}"{hidden(key)}>{row.get(key, "")}</td>' if key in self.by_id
                else f'<td class="note-cell">{row.get(key, "")}</td>'
                for key in cols
            ) + "</tr>"
            for row in block["rows"]
        )
        caption = f'<figcaption>{icon("table")}{block["title"]}</figcaption>' if block["title"] else ""
        return (
            f'<figure class="map" data-langs="{",".join(ids)}">{caption}<div class="map-scroll" tabindex="0">'
            f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div></figure>"
        )

    def render_block(self, block: dict) -> str:
        kind = block["type"]
        if kind == "p":
            return f'<p>{block["html"]}</p>'
        if kind == "h3":
            return f'<h3>{block["html"]}</h3>'
        if kind == "list":
            tag = "ol" if block["ordered"] else "ul"
            return f"<{tag}>" + "".join(f"<li>{item}</li>" for item in block["items"]) + f"</{tag}>"
        if kind == "code":
            return self.code_figure(block)
        if kind == "compare":
            return self.compare_card(block)
        if kind == "map":
            return self.map_table(block)
        if kind in ("tip", "warn"):
            title = ""
            if block["title"]:
                title = f'<h4>{icon("warn" if kind == "warn" else "bulb")}{block["title"]}</h4>'
            return f'<aside class="note {kind}">{title}<div class="note-body">{self.render_blocks(block["blocks"])}</div></aside>'
        if kind == "more":
            return (
                f'<details class="more"><summary>{icon("chevron")}<span>{block["title"]}</span>'
                f'<span class="tag">选读</span></summary><div class="more-body">{self.render_blocks(block["blocks"])}</div></details>'
            )
        return ""

    def render_blocks(self, blocks: list[dict]) -> str:
        return "".join(self.render_block(block) for block in blocks)

    # ---------- 页面 ----------

    def sidebar(self, root: str, active: str) -> str:
        def chapter_item(chapter: dict) -> str:
            is_active = chapter["id"] == active
            sections = "".join(
                f'<li><a {self.link(root, chapter["id"], section["id"])} data-sec="{section["id"]}">{section["title"]}</a></li>'
                for section in chapter["sections"]
            )
            current = ' aria-current="page"' if is_active else ""
            return (
                f'<li class="side-ch{" is-active" if is_active else ""}" data-ch="{chapter["id"]}">'
                f'<a class="side-link" {self.link(root, chapter["id"])}{current}>'
                f'<span class="n">{chapter["no"]}</span><span class="t">{esc(chapter["title"])}</span>'
                f'<span class="tick">{icon("check")}</span></a>'
                f'<div class="side-secs"><ol>{sections}</ol></div></li>'
            )

        sheet = (
            '<section class="side-part"><h2>工具</h2><ol>'
            f'<li class="side-ch{" is-active" if active == self.sheet_id else ""}" data-ch="{self.sheet_id}">'
            f'<a class="side-link" {self.link(root, self.sheet_id)}><span class="n">{icon("table")}</span>'
            '<span class="t">速查表</span></a></li></ol></section>'
        )

        def category_items(category: dict) -> str:
            groups = "".join(
                f'<section class="side-part"><h2>{esc(part)}</h2><ol>'
                + "".join(chapter_item(c) for c in category["chapters"] if c["part"] == part)
                + "</ol></section>"
                for part in category["parts"]
            )
            return groups + (sheet if category is self.sheet_category else "")

        # 所有大类都写进页面，只显示当前这一类。单文件预览版切换页面时不会重新生成目录
        current = active if active in self.category_by_id else next(
            (c["category"] for c in self.chapters if c["id"] == active), self.sheet_category["id"]
        )
        picker = ""
        if len(self.categories) > 1:
            options = "".join(
                f'<option value="{c["id"]}"{" selected" if c["id"] == current else ""}>{esc(c["name"])}</option>'
                for c in self.categories
            )
            picker = f'<label class="side-pick"><select id="side-cat" aria-label="选择大类" autocomplete="off">{options}</select></label>'
        return picker + "".join(
            f'<div class="side-cat" data-cat="{c["id"]}"{"" if c["id"] == current else " hidden"}>{category_items(c)}</div>'
            for c in self.categories
        )

    def home_main(self, root: str) -> str:
        chapters = self.chapters
        hero = next((b for c in chapters for b in chapter_blocks(c) if b.get("anchor") == "hero"), None)

        def category_card(category: dict) -> str:
            return (
                f'<li><a class="cat-card" {self.link(root, category["id"])}><b>{esc(category["name"])}</b>'
                f'<span class="cat-sum">{esc(category["summary"])}</span>'
                f'<span class="cat-foot">{len(category["chapters"])} 章 · {reading_time(category)}{icon("chevron")}</span></a></li>'
            )

        return (
            '<div class="home"><section class="hero">'
            f"<h1>{esc(self.site_name)}</h1>"
            f'<p class="lede">{esc(self.site_lede)}</p>'
            # 只有读过的人才需要这个按钮，由 app.js 显示
            f'<div class="cta" hidden><a class="btn primary" id="cta-start" {self.link(root, chapters[0]["id"])}>开始学习</a></div>'
            "</section>"
            f'<ul class="cat-grid">{"".join(category_card(c) for c in self.categories)}</ul>'
            f'{self.compare_card(hero, compact=True) if hero else ""}'
            '<footer class="foot">Python 语言部分改写自 <a href="https://docs.python.org/zh-cn/3.12/tutorial/index.html" '
            'target="_blank" rel="noopener">Python 3.12 官方教程</a>，示例基于 Python 3.12、Java 21 和 Kotlin 2。'
            "“Python”是 Python 软件基金会（PSF）的注册商标，本站与 PSF 无关。</footer></div>"
        )

    def category_main(self, category: dict, root: str) -> str:
        chapters = category["chapters"]
        compares = sum(c["compares"] for c in chapters)
        stats = [f"{len(chapters)} 章"] + ([f"{compares} 组对比"] if compares else []) + [reading_time(category)]

        def toc_item(chapter: dict) -> str:
            return (
                f'<li><a {self.link(root, chapter["id"])}><span class="toc-no">{chapter["no"]}</span>'
                f'<span class="toc-text"><b>{esc(chapter["title"])}</b><span>{chapter["lede"]}</span></span>'
                f'<span class="toc-meta">{chapter["minutes"]} 分钟</span>'
                f'<span class="toc-meta is-done" hidden>{icon("check")}已读</span>{icon("chevron")}</a></li>'
            )

        parts = "".join(
            f'<section class="part"><h2>{esc(part)}</h2><ol class="toc">'
            + "".join(toc_item(c) for c in chapters if c["part"] == part)
            + "</ol></section>"
            for part in category["parts"]
        )
        sheet = f'<a class="btn quiet" {self.link(root, self.sheet_id)}>速查表</a>' if category is self.sheet_category else ""
        return (
            f'<div class="home"><a class="back" {self.link(root, "home")}>{icon("chevron")}全部分类</a>'
            f'<section class="hero cat-hero"><h1>{esc(category["name"])}</h1><p class="lede">{esc(category["summary"])}</p>'
            f'<div class="cta"><a class="btn primary" id="cta-start" data-cat="{category["id"]}" '
            f'{self.link(root, chapters[0]["id"])}>开始学习</a>{sheet}</div>'
            f'<p class="hero-meta">{" · ".join(stats)}</p></section>'
            f'<div class="parts">{parts}</div></div>'
        )

    def chapter_main(self, chapter: dict, root: str) -> str:
        category = self.category_by_id[chapter["category"]]
        index = chapter["no"] - 1
        prev_ch = category["chapters"][index - 1] if index else None
        next_ch = category["chapters"][index + 1] if index + 1 < len(category["chapters"]) else None
        intro =f'<div class="flow intro">{self.render_blocks(chapter["intro"])}</div>' if chapter["intro"] else ""
        sections = "".join(
            f'<section class="sec" id="{s["id"]}"><h2>{s["title"]}</h2>'
            f'<div class="flow">{self.render_blocks(s["blocks"])}</div></section>'
            for s in chapter["sections"]
        )
        recap = ""
        if chapter["recap"]:
            items = "".join(f'<li>{icon("check")}<span>{item}</span></li>' for item in chapter["recap"])
            recap = f'<section class="recap"><h2>本章要点</h2><ul>{items}</ul></section>'
        sources = "".join(
            f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}{icon("link")}</a>'
            for s in chapter["sources"]
        )
        previous = (
            f'<a class="prev" {self.link(root, prev_ch["id"])}><span>上一章</span><b>{esc(prev_ch["title"])}</b></a>'
            if prev_ch else ""
        )
        if next_ch:
            following = f'<a class="next" {self.link(root, next_ch["id"])}><span>下一章</span><b>{esc(next_ch["title"])}</b></a>'
        elif category is self.sheet_category:
            following = f'<a class="next" {self.link(root, self.sheet_id)}><span>学完了</span><b>速查表</b></a>'
        else:
            following = f'<a class="next" {self.link(root, category["id"])}><span>学完了</span><b>{esc(category["name"])}目录</b></a>'
        compares = f'<li>{icon("swap")}{chapter["compares"]} 组对比</li>' if chapter["compares"] else ""
        content = self.link_references(f"{intro}{sections}", chapter, root)
        versions = f'<li>基于 {esc(chapter["versions"])}</li>' if chapter["versions"] else ""
        return (
            f'<article class="doc"><header class="doc-head"><h1>{esc(chapter["title"])}</h1>'
            f'<p class="lede">{chapter["lede"]}</p><ul class="meta">'
            f'<li><span><a {self.link(root, category["id"])}>{esc(category["name"])}</a> · 第 {chapter["no"]} 章</span></li>'
            f'<li>{icon("clock")}{chapter["minutes"]} 分钟</li>'
            f'{compares}{versions}</ul></header>'
            f'{content}<div class="doc-tail">{recap}<p class="sources">参考资料：{sources}</p>'
            f'<nav class="pager" id="pager" aria-label="翻页">{previous}{following}</nav></div></article>'
        )

    def sheet_main(self, root: str) -> str:
        groups = ""
        for chapter in self.sheet_category["chapters"]:
            maps = [b for b in chapter_blocks(chapter) if b["type"] == "map"]
            if maps:
                groups += (
                    f'<section class="sheet-group"><h2><a {self.link(root, chapter["id"])}>{esc(chapter["title"])}</a></h2>'
                    + "".join(self.map_table(m) for m in maps) + "</section>"
                )
        return (
            '<article class="doc"><header class="doc-head"><h1>速查表</h1>'
            '<p class="lede">写代码时忘了怎么写，来这里查。表格汇总自各章，右上角可以切换语言。</p>'
            f'<label class="sheet-filter">{icon("search")}<input id="sheet-q" type="search" autocomplete="off" '
            'placeholder="过滤，例如 ArrayList、dict、when" aria-label="过滤速查表"></label></header>'
            f'<div class="flow">{groups}<p class="sheet-empty" id="sheet-empty" hidden>没有匹配的条目，换个关键词试试。</p></div></article>'
        )

    def not_found_html(self, root: str) -> str:
        return (
            '<article class="doc"><header class="doc-head"><h1>页面不存在</h1>'
            '<p class="lede">这个地址没有内容，可能是链接写错了。</p></header>'
            f'<p class="sources"><a {self.link(root, "home")}>返回首页</a></p></article>'
        )

    def main_html(self, page: dict, root: str) -> str:
        if page["view"] == "home":
            return self.home_main(root)
        if page["view"] == "category":
            return self.category_main(page["category"], root)
        if page["view"] == "sheet":
            return self.sheet_main(root)
        return self.chapter_main(page["chapter"], root)

    def shell(self, template: str, page: dict, root: str, main: str, search_url: str) -> str:
        theme_icons = "".join(f'<span data-t="{name}">{icon(name)}</span>' for name in ("auto", "sun", "moon"))
        options = "".join(f'<option value="{lang}">{esc(self.by_id[lang]["name"])}</option>' for lang in self.others)
        attrs = f'data-root="{root}" data-base="{self.base}" data-search="{root}{search_url}"'
        replacements = {
            "{{SITE_NAME}}": esc(self.site_name),
            "{{HOME_LINK}}": self.link(root, "home"),
            "{{ICON_MENU}}": icon("menu"),
            "{{ICON_SEARCH}}": icon("search"),
            "{{THEME_ICONS}}": theme_icons,
            "{{LANG_OPTIONS}}": options,
            "{{SIDE}}": self.sidebar(root, page["id"]),
            "{{MAIN_ATTRS}}": attrs,
            "{{MAIN}}": main,
        }
        for key, value in replacements.items():
            template = template.replace(key, value)
        return template

    # ---------- 搜索索引 ----------

    def search_index(self) -> list[dict]:
        index = []

        def add(kind, title, sub, page, frag, text, rank):
            index.append({"kind": kind, "title": title, "sub": sub, "page": page,
                          "frag": frag, "text": text, "rank": rank})

        for category in self.categories:
            add("大类", category["name"], category["summary"], category["id"], "", "", 3)

        for chapter in self.chapters:
            category = self.category_by_id[chapter["category"]]["name"]
            add("章节", f'{chapter["no"]}. {chapter["title"]}', f'{category} · {plain(chapter["lede"])}', chapter["id"], "", "", 3)
            for section in chapter["sections"]:
                section_title = plain(section["title"])
                add("小节", section_title, chapter["title"], chapter["id"], section["id"], "", 2)
                for block in walk(section["blocks"]):
                    if block["type"] == "compare":
                        code = "\n".join(c["code"] for c in block["cols"].values())
                        table = "\n".join(
                            plain(v) for row in (block["table"] or {"rows": []})["rows"] for v in row.values()
                        )
                        notes = "\n".join(plain(n) for n in block["notes"].values())
                        add("对比", plain(block["title"]), f'{chapter["title"]} · {section_title}', chapter["id"],
                            block["id"], f'{code}\n{table}\n{notes}\n{plain(block.get("take"))}', 2)
                    elif block["type"] == "map":
                        keys = [key for key in block["cols"] if key in self.by_id]
                        for row in block["rows"]:
                            first, *rest = keys
                            pairs = [f'{self.by_id[k]["name"]}: {plain(row.get(k, ""))}' for k in rest if plain(row.get(k, ""))]
                            add("对照", plain(row.get(first, "")), "  ·  ".join(pairs), chapter["id"], section["id"],
                                "\n".join(plain(v) for v in row.values()), 1)
                    elif block.get("html"):
                        add("正文", section_title, chapter["title"], chapter["id"], section["id"], plain(block["html"]), 0)
        return index
