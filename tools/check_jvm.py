#!/usr/bin/env python3
"""编译标了 no-run 的 Java 和 Kotlin 示例，确认用到的库和方法真实存在。

    .venv/bin/python tools/check_jvm.py                  # 编译全部示例
    .venv/bin/python tools/check_jvm.py java             # 只编译 Java
    .venv/bin/python tools/check_jvm.py kotlin fastapi   # 只编译某一章的 Kotlin

这些示例依赖 Spring Boot、OpenAI Java SDK 等框架，只编译不运行。依赖版本写在
tools/jvm/build.gradle.kts，需要 JDK 21、Gradle 和 kotlinc。

示例是代码片段，脚本把它们放进带常用导入的文件里编译。片段缺的声明写成 § 隐藏行，
这里的通配导入有冲突时，也用隐藏行写一条明确的 import。
依赖 Android 框架的片段编译不了，靠 ANDROID_ONLY 跳过，FRAGMENT_CHAPTERS 里的章节整章跳过。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
JVM = TOOLS / "jvm"
sys.path.insert(0, str(TOOLS.parent))
import build  # noqa: E402

ANDROID_ONLY = ("hiltRule", "@InstallIn", "SupportSQLiteDatabase", "helper.writableDatabase", "AppDatabase")
# 这几章的 no-run 片段是 Gradle 配置、XML 或零散语句，不是能编译的代码
FRAGMENT_CHAPTERS = {"input-output", "modules", "standard-library", "virtual-environments"}

JAVA_IMPORTS = """
java.util.*; java.util.concurrent.*; java.util.function.*; java.util.stream.*; java.time.*; java.io.*;
java.net.*; java.net.http.*; java.net.http.HttpResponse.*; java.sql.*; java.nio.file.*;
org.springframework.web.bind.annotation.*; org.springframework.stereotype.*;
org.springframework.beans.factory.annotation.*; org.springframework.web.server.*;
org.springframework.web.servlet.mvc.method.annotation.*; org.springframework.boot.*;
org.springframework.boot.autoconfigure.*; org.springframework.data.jpa.repository.*;
org.springframework.transaction.annotation.*; jakarta.persistence.*; jakarta.validation.*;
jakarta.validation.constraints.*; reactor.core.publisher.*; reactor.core.scheduler.*;
com.fasterxml.jackson.databind.*; com.fasterxml.jackson.annotation.*; org.flywaydb.core.api.migration.*;
org.junit.jupiter.api.*; org.junit.jupiter.params.*; org.junit.jupiter.params.provider.*;
org.springframework.test.web.servlet.*; org.springframework.test.context.bean.override.mockito.*;
org.springframework.boot.webmvc.test.autoconfigure.*; org.springframework.boot.test.context.*;
org.springframework.boot.context.properties.*; org.springframework.boot.context.properties.bind.*;
com.openai.client.*; com.openai.client.okhttp.*; com.openai.models.*; com.openai.models.chat.completions.*;
com.openai.models.embeddings.*; com.openai.errors.*; com.openai.core.*;
dev.langchain4j.agent.tool.*; dev.langchain4j.service.*; dev.langchain4j.memory.chat.*;
dev.langchain4j.model.chat.*; dev.langchain4j.model.openai.*; dev.langchain4j.model.embedding.*;
dev.langchain4j.data.segment.*; dev.langchain4j.data.embedding.*; dev.langchain4j.data.message.*;
dev.langchain4j.store.embedding.*; dev.langchain4j.store.embedding.inmemory.*;
dev.langchain4j.rag.content.retriever.*;
"""
# 单个类的导入优先于通配导入，这些类名在上面的包里有重名
JAVA_EXACT = """
org.springframework.http.HttpStatus; org.springframework.data.jpa.repository.Query;
org.springframework.data.jpa.repository.Lock; dev.langchain4j.model.chat.ChatModel;
dev.langchain4j.model.embedding.EmbeddingModel; dev.langchain4j.service.UserMessage;
dev.langchain4j.service.SystemMessage; java.nio.file.Path; java.util.concurrent.Future;
java.net.http.HttpRequest;
"""
JAVA_STATIC = """
org.mockito.Mockito.*; org.mockito.ArgumentMatchers.*; org.junit.jupiter.api.Assertions.*;
org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
"""
KOTLIN_IMPORTS = """
kotlinx.coroutines.*; kotlinx.coroutines.flow.*; kotlinx.coroutines.channels.*; kotlinx.coroutines.test.*;
kotlinx.serialization.*; kotlinx.serialization.json.*; okhttp3.*; okhttp3.sse.*; javax.inject.*;
org.junit.jupiter.api.Test; java.util.concurrent.TimeUnit; java.time.*; kotlin.time.*; kotlin.test.*;
io.mockk.*; org.junit.jupiter.api.*; org.junit.jupiter.params.*; org.junit.jupiter.params.provider.*;
dev.langchain4j.agent.tool.*; dev.langchain4j.service.*; dev.langchain4j.memory.chat.*;
dev.langchain4j.model.chat.*; dev.langchain4j.model.openai.*;
"""
KOTLIN_ANDROID = "androidx.room.*"
KOTLIN_RETROFIT = "retrofit2.http.*; retrofit2.HttpException"
KOTLIN_OPENAI = """
com.openai.client.okhttp.OpenAIOkHttpClient; com.openai.client.OpenAIClient;
com.openai.models.chat.completions.*; com.openai.models.embeddings.*; com.openai.errors.*
"""


def import_lines(text: str, prefix: str, end: str) -> list[str]:
    return [f"{prefix}{name}{end}" for name in re.split(r";\s*", text.strip()) if name.strip()]


def java_header() -> str:
    lines = import_lines(JAVA_EXACT, "import ", ";") + import_lines(JAVA_IMPORTS, "import ", ";")
    return "\n".join(lines + import_lines(JAVA_STATIC, "import static ", ";"))


def kotlin_header(code: str) -> str:
    lines = import_lines(KOTLIN_IMPORTS, "import ", "")
    room = re.search(r"@(Dao|PrimaryKey|Database)\b", code)
    lines += import_lines(KOTLIN_ANDROID if room else KOTLIN_RETROFIT, "import ", "")
    if "OpenAI" in code or "ChatCompletion" in code or "Embedding" in code:
        lines += import_lines(KOTLIN_OPENAI, "import ", "")
    return "\n".join(lines)


def collect(lang: str, only: set[str]) -> list[tuple[str, str]]:
    found = []
    for chapter in build.load_course()["chapters"]:
        if chapter["id"] in FRAGMENT_CHAPTERS or (only and chapter["id"] not in only):
            continue
        blocks = chapter["intro"] + [b for s in chapter["sections"] for b in s["blocks"]]
        for block in build.walk(blocks):
            codes = [block] if block["type"] == "code" else []
            if block["type"] == "compare":
                codes = list(block["cols"].values())
            for code in codes:
                skip = any(token in code["src"] for token in ANDROID_ONLY)
                if code.get("col") == lang and not code["run"] and not skip:
                    title = re.sub("<.*?>", "", block.get("title", "代码块"))
                    found.append((f"{chapter['id']} · {title}", code["src"]))
    return found


def write_sources(lang: str, items: list[tuple[str, str]], source: Path) -> None:
    shutil.rmtree(source, ignore_errors=True)
    for i, (_, code) in enumerate(items):
        lifted = "\n".join(line for line in code.splitlines() if line.startswith("import "))
        body = "\n".join(line for line in code.splitlines() if not line.startswith("import "))
        folder = source / f"s{i}"
        folder.mkdir(parents=True)
        if lang == "java":
            text = f"package s{i};\n{lifted}\n{java_header()}\nclass S {{\n{body}\n}}\n"
            (folder / "S.java").write_text(text, "utf-8")
        else:
            text = f"package s{i}\n{lifted}\n{kotlin_header(code)}\n{body}\n"
            (folder / "S.kt").write_text(text, "utf-8")


def gradle() -> str:
    found = shutil.which("gradle") or next(iter(sorted(Path.home().glob(".gradle/wrapper/dists/*/*/*/bin/gradle"))), None)
    if not found:
        sys.exit("缺少 gradle")
    return str(found)


def classpath(env: dict) -> str:
    target = JVM / "classpath.txt"
    newest = (JVM / "build.gradle.kts").stat().st_mtime
    if not target.exists() or target.stat().st_mtime < newest:
        # 用单独的 Gradle 目录，不受用户全局代理等配置影响
        gradle_env = {**env, "GRADLE_USER_HOME": str(JVM / ".gradle-home")}
        subprocess.run([gradle(), "--no-daemon", "-q", "classpath"], cwd=JVM, env=gradle_env, check=True)
    return target.read_text("utf-8").strip()


def compile_all(lang: str, source: Path, output: Path, cp: str, env: dict) -> tuple[int, str]:
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True)
    if lang == "java":
        files = [str(p) for p in source.rglob("*.java")]
        command = ["javac", "-J-Duser.language=en", "-proc:none", "-nowarn", "-Xmaxerrs", "2000",
                   "-cp", cp, "-d", str(output), *files]
    else:
        command = ["kotlinc", "-no-stdlib", "-no-reflect", "-nowarn", "-jvm-target", "21",
                   "-opt-in=kotlinx.serialization.ExperimentalSerializationApi",
                   "-cp", cp, "-d", str(output), str(source)]
    done = subprocess.run(command, capture_output=True, text=True, env=env)
    return done.returncode, done.stdout + done.stderr


def check(lang: str, only: set[str], cp: str, env: dict) -> bool:
    items = collect(lang, only)
    source = JVM / "build" / lang / "src"
    write_sources(lang, items, source)
    status, output = compile_all(lang, source, JVM / "build" / lang / "out", cp, env)
    errors = re.findall(r"/src/(s\d+)/S\.(?:java|kt):(\d+)(?::\d+)?: error: (.*)", output)
    for folder, line, message in dict.fromkeys(errors):
        file = next((source / folder).iterdir())
        code = file.read_text("utf-8").splitlines()[int(line) - 1].strip()
        print(f"✗ {items[int(folder[1:])][0]} · {lang}\n  {message}\n  > {code}\n")
    if status and not errors:
        print(output[-1500:])
    failed = len({e[0] for e in errors})
    print(f"{lang}：通过 {len(items) - failed}/{len(items)}")
    return status == 0


def main() -> None:
    wanted = [a for a in sys.argv[1:] if a in ("java", "kotlin")] or ["java", "kotlin"]
    only = {a for a in sys.argv[1:] if a not in ("java", "kotlin")}
    env = dict(os.environ)
    if missing := [c for c in ("javac", "kotlinc") if shutil.which(c) is None]:
        sys.exit(f"缺少命令：{', '.join(missing)}")
    cp = classpath(env)
    ok = [check(lang, only, cp, env) for lang in wanted]
    sys.exit(0 if all(ok) else 1)


if __name__ == "__main__":
    main()
