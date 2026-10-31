#!/usr/bin/env python3
"""运行 content/ 里的全部示例，确认代码能跑、`=>` 注释写的结果和真实输出一致。

    python3 tools/verify.py                 # 校验全部语言
    python3 tools/verify.py python kotlin   # 只校验指定语言

校验规则：
    - `# => 值` / `// => 值` 必须按顺序出现在程序输出里
    - Python 里裸写的表达式带 `# =>` 时，按 repr 结果比较
    - ```output 块要求和输出完全一致
    - 以 § 开头的隐藏行参与运行，但不展示给读者
    - 带 no-run 标记的代码块跳过

新增语言时，在 RUNNERS 里加一个函数即可。
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build  # noqa: E402

ARROW = re.compile(r"(?:#|//)\s*=>\s*(.*?)\s*$")
TIMEOUT = 180


def expected_values(src: str) -> list[str]:
    return [m.group(1) for line in src.splitlines() if (m := ARROW.search(line))]


def run_python(src: str, workdir: Path) -> tuple[int, str]:
    lines = src.splitlines()

    class Wrap(ast.NodeTransformer):
        def visit_Expr(self, node: ast.Expr):
            is_print = isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "print"
            if ARROW.search(lines[node.end_lineno - 1]) and not is_print:
                call = ast.parse("print(repr(None))").body[0]
                call.value.args[0].args[0] = node.value
                return ast.copy_location(call, node)
            return node

    tree = Wrap().visit(ast.parse(src))
    ast.fix_missing_locations(tree)
    script = workdir / "snippet.py"
    script.write_text(ast.unparse(tree), "utf-8")
    done = subprocess.run([sys.executable, "snippet.py"], cwd=workdir, capture_output=True,
                          text=True, timeout=TIMEOUT)
    return done.returncode, done.stdout if done.returncode == 0 else done.stdout + done.stderr


def run_java(src: str, workdir: Path) -> tuple[int, str]:
    # jshell 按行判断语句是否结束，所以要把换行的链式调用接回上一行
    joined = re.sub(r"\n\s*(?=(?:\.|\? |: )\S)", " ", src)
    script = workdir / "snippet.jsh"
    script.write_text(joined + "\n/exit\n", "utf-8")
    done = subprocess.run(["jshell", "-J-Duser.language=en", "--feedback", "silent", str(script)],
                          cwd=workdir, capture_output=True, text=True, timeout=TIMEOUT,
                          stdin=subprocess.DEVNULL)
    failed = re.search(r"^\|?\s*(Error:|Exception\b)|^\S*Exception", done.stdout, re.M)
    return (1 if failed else 0), done.stdout + done.stderr


def run_kotlin(src: str, workdir: Path) -> tuple[int, str]:
    script = workdir / "snippet.kts"
    script.write_text(src + "\n", "utf-8")
    done = subprocess.run(["kotlinc", "-script", str(script)], cwd=workdir, capture_output=True,
                          text=True, timeout=TIMEOUT)
    return done.returncode, done.stdout if done.returncode == 0 else done.stdout + done.stderr


RUNNERS = {"python": (run_python, "python3"), "java": (run_java, "jshell"), "kotlin": (run_kotlin, "kotlinc")}


def collect() -> list[tuple[str, str, dict]]:
    found = []
    for chapter in build.load_course()["chapters"]:
        blocks = chapter["intro"] + [b for s in chapter["sections"] for b in s["blocks"]]
        for block in build.walk(blocks):
            if block["type"] == "code":
                found.append((chapter["id"], "代码块", block))
            elif block["type"] == "compare":
                for code in block["cols"].values():
                    found.append((chapter["id"], re.sub("<.*?>", "", block["title"]), code))
    return found


def check(item: tuple[str, str, dict]) -> tuple[str, str | None]:
    chapter, title, code = item
    label = f"{chapter} · {title} · {code['col']}"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            status, output = RUNNERS[code["col"]][0](code["src"], Path(tmp))
        except subprocess.TimeoutExpired:
            return label, "运行超时"
    if status != 0:
        return label, "运行失败\n" + output.strip()[-900:]

    got = [line.rstrip() for line in output.splitlines()]
    if "output" in code:
        want = [line.rstrip() for line in code["output"].splitlines()]
        if got != want:
            return label, f"输出不一致\n  期望 {want}\n  实际 {got}"
    cursor = 0
    for value in expected_values(code["src"]):
        while cursor < len(got) and got[cursor] != value:
            cursor += 1
        if cursor == len(got):
            return label, f"没有在输出里找到 {value!r}\n  实际 {got}"
        cursor += 1
    return label, None


def main() -> None:
    wanted = sys.argv[1:] or list(RUNNERS)
    items = [i for i in collect() if i[2]["run"] and i[2]["col"] in wanted]
    missing = {RUNNERS[w][1] for w in wanted if shutil.which(RUNNERS[w][1]) is None}
    if missing:
        sys.exit(f"缺少命令：{', '.join(sorted(missing))}")

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(check, items))

    failures = [(label, why) for label, why in results if why]
    for label, why in failures:
        print(f"✗ {label}\n  {why}\n")

    skipped = sum(1 for i in collect() if not i[2]["run"] and i[2]["col"] in wanted)
    print(f"通过 {len(results) - len(failures)}/{len(results)}，跳过 {skipped} 个不可运行的片段")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
