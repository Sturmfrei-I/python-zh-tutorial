---
id: getting-started
part: 语言基础
title: 上手运行
lede: 跑起第一段代码，弄清 Python 和 JVM 语言在运行方式上的差别。
source: 课前甜点 | appetite.html ; 使用解释器 | interpreter.html ; 交互式编辑 | interactive.html ; 附录 | appendix.html
seo_title: Python 入门教程：安装、运行第一个程序，和 Java、Kotlin 有什么不同
seo_description: Python 入门第一步：安装 Python 3.12，运行第一段代码，理解解释执行、动态类型和缩进语法。每个知识点都和 Java、Kotlin 对比，适合有编程经验的开发者快速上手。
---

## 三个根本差别 {#mindset}

Python 的语法很快就能上手。真正需要适应的是下面三点。

- **没有单独的编译步骤。** `python3 app.py` 直接运行源文件，字节码在后台自动生成。除语法错误外，大部分错误要运行到那一行才会暴露。
- **类型属于值，变量没有类型。** 同一个变量可以先后指向数字和字符串，传错类型也要到运行时才知道。
- **函数、类、模块都是普通对象。** 它们可以赋值给变量、放进列表、当参数传递。`def`、`class`、`import` 都是运行时执行的语句。

:::map 运行模型对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `python3 app.py` | `javac` + `java` | `kotlinc` + `java` | Java 11 起也能用 `java App.java` 直接运行单个文件 |
| CPython 解释器 | JVM | JVM | |
| `.pyc` 字节码 | `.class` | `.class` | Python 自动放在 `__pycache__/`，不用手动管理 |
| `python3` 交互模式 | `jshell` | Kotlin Notebook | 验证想法最快的方式 |
:::

:::tip 示例用的版本
示例基于 Python 3.12、Java 21 和 Kotlin 2。如果你主要用 Java 8，可能会看到一些没见过的写法：`List.of`（Java 9）、`var`（Java 10）、文本块（Java 15）、`record` 和 `Stream.toList()`（Java 16）。
:::

## Hello World {#hello}

把下面一行存为 `hello.py`，再执行 `python3 hello.py` 就能看到输出。

:::compare 程序入口
```python
print("Hello, World!")
```
```java
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```
```kotlin
fun main() {
    println("Hello, World!")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 程序入口 | 文件顶层语句直接执行 | `main` 方法 | `main` 函数 |
| 是否需要类 | 不需要 | 需要 | = |
| 输出语句 | `print()` | `System.out.println()` | `println()` |
| 语句结尾 | 不写分号 | 必须写分号 | = |

> 要点: Python 脚本像一段自上而下的指令。需要区分「被运行」和「被导入」时，再用第 6 章的 `if __name__ == "__main__"`。
:::

## 运行代码的几种方式 {#run}

macOS 用 `brew install python@3.12`，Windows 从 python.org 下载安装包，Linux 大多已经预装。Windows 上命令通常是 `python` 或 `py`。

```bash
python3 --version          # 查看版本
python3 hello.py           # 运行脚本
python3                    # 进入交互模式，用 exit() 或 Ctrl-D 退出
python3 -c "print(1 + 1)"  # 运行一行代码
python3 -m http.server     # 把标准库模块当程序运行
```

交互模式是学习期最常用的工具。提示符 `>>>` 后输入表达式，回车就能看到结果，不用写 `print`。后面的示例里，`# =>` 表示这一行的结果。

遇到不熟悉的对象，用 `help(obj)` 看文档，用 `dir(obj)` 列出它的属性和方法。

:::tip 编辑器
如果你习惯 IntelliJ IDEA，PyCharm 的操作和快捷键几乎一致。VS Code 加 Python 扩展也够用。
:::

:::more 交互模式的实用技巧
- 按 `Tab` 补全名字，按方向键翻历史命令
- `_` 保存上一个表达式的结果
- `python3 -i app.py` 运行脚本后留在交互模式，可以检查变量
- 环境变量 `PYTHONSTARTUP` 指向一个文件，每次进入交互模式时自动执行
- 想要语法高亮和更强的补全，可以安装 `ipython`
:::

:::more 脚本头和源文件编码
在 Unix 系统上，给脚本第一行加 `#!/usr/bin/env python3`，再执行 `chmod +x hello.py`，就可以用 `./hello.py` 运行。源文件默认按 UTF-8 解码，中文变量名和字符串都没问题。极少数情况要用别的编码时，才需要在文件开头写 `# -*- coding: cp1252 -*-`。
:::

## 缩进就是语法 {#indent}

Python 用缩进表示代码块，没有花括号和分号。冒号开启一个新块，缩进回退时块结束。

:::compare 代码块
```python
for n in [1, 2, 3]:
    if n % 2 == 0:
        print(n, "是偶数")
print("结束")
```
```java
for (int n : List.of(1, 2, 3)) {
    if (n % 2 == 0) {
        System.out.println(n + " 是偶数");
    }
}
System.out.println("结束");
```
```kotlin
for (n in listOf(1, 2, 3)) {
    if (n % 2 == 0) {
        println("$n 是偶数")
    }
}
println("结束")
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 代码块边界 | 缩进 | 花括号 | 花括号 |
| 缩进的作用 | 语法的一部分 | 只是代码风格 | 只是代码风格 |
| 条件括号 | 不写 | 必须写 | 必须写 |
| 代码块开头 | 冒号 | `{` | `{` |
| 嵌套逻辑 | 外层控制内层执行 | = | = |

> 要点: 同一个块的缩进必须一致，不一致时报 `IndentationError`。交给编辑器处理，别混用 Tab 和空格。
:::

注释用 `#`，没有 `/* */` 这样的多行注释。一行写不下时，放在括号里的内容可以直接换行，不需要续行符。

```python
total = (1 + 2 + 3
         + 4 + 5)
print(total)  # => 15
```

:::recap
- `python3 app.py` 直接运行源文件，没有手动编译步骤
- 脚本从上到下执行，不需要 `main` 和类
- 缩进决定代码块，冒号开启新块，标准缩进是 4 个空格
- 交互模式是最快的试验场，`# =>` 表示代码的结果
:::
