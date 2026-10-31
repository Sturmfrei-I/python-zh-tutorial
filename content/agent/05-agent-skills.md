---
id: agent-skills
part: 连接外部能力
title: Agent Skills
lede: 工具给 Agent 手脚，Skill 给它经验。把做事的方法写进文件，需要时再读取，既不占上下文，又能跟着项目一起维护。
source: Agent Skills 规范 | https://agentskills.io/specification ; Agent Skills 简介 | https://agentskills.io/home ; MCP 规范 | https://modelcontextprotocol.io/specification/latest
versions: Agent Skills 规范 · Python 3.12
seo_title: Agent Skills 教程：SKILL.md 格式和渐进式加载
seo_description: 讲解 Agent Skills 开放标准：SKILL.md 的格式、name 和 description 怎么写、渐进式披露、在自己的 Agent 里实现加载，以及 Skill、工具和 MCP 的区别。
---

## 什么是 Skill {#what}

Skill 是一个文件夹，里面有一份 `SKILL.md`，写着完成某类任务的方法。需要时 Agent 读取它，照着做。还可以附带脚本和参考资料。

比如「按公司规范写周报」「发布一个新版本」这类任务，步骤和注意事项都很具体。全写进系统提示会占满上下文，大多数对话又用不上，Skill 解决的就是这个问题。

Agent Skills 是一个开放格式，最早由 Anthropic 提出，现在多个 Agent 产品都支持。

## 文件格式 {#format}

最小的 Skill 只有一个文件。文件夹名就是 Skill 的名字。

```text
weekly-report/
├── SKILL.md          # 必须有
├── scripts/          # 可选，能运行的脚本
├── references/       # 可选，参考资料
└── assets/           # 可选，模板和数据
```

`SKILL.md` 开头是 YAML 元数据，后面是 Markdown 正文。

```markdown
---
name: weekly-report
description: 按团队模板写周报。用户要写周报、总结本周工作时使用。
---

# 写周报

1. 读取 references/template.md 里的模板
2. 从提交记录里整理本周完成的工作
3. 风险和下周计划各写三条以内
```

只有两个字段是必须的：

| 字段 | 要求 |
| --- | --- |
| `name` | 最多 64 个字符，只能有小写字母、数字和连字符，和文件夹名相同 |
| `description` | 最多 1024 个字符，写清楚做什么和什么时候用 |

## 渐进式加载 {#disclosure}

Skill 省上下文的关键，是内容分三层，用到才读：

| 层级 | 内容 | 什么时候读取 | 大小 |
| --- | --- | --- | --- |
| 元数据 | `name` 和 `description` | 启动时，所有 Skill 都读 | 每个约 100 token |
| 指令 | `SKILL.md` 正文 | 决定使用这个 Skill 时 | 建议少于 5000 token |
| 资源 | `scripts`、`references` 里的文件 | 真正需要时 | 按需 |

一个 Agent 可以装几十个 Skill，平时只多占几千 token。正文建议控制在 500 行以内，更详细的内容拆到 `references` 里。

## 实现加载 {#load}

用的 Agent 产品一般已经内置了 Skill 支持。自己写 Agent 时实现起来也很简单，只要两步：启动时把元数据放进系统提示，再提供一个读取正文的工具。

:::compare 扫描 Skill 目录
```python
§ import pathlib
§ root = pathlib.Path("skills/weekly-report")
§ root.mkdir(parents=True)
§ (root / "SKILL.md").write_text("""---
§ name: weekly-report
§ description: 按团队模板写周报
§ ---
§ 
§ 1. 读取模板
§ 2. 整理本周工作
§ """, "utf-8")
from pathlib import Path

def parse(path: Path) -> tuple[dict[str, str], str]:
    _, header, body = path.read_text("utf-8").split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in header.strip().splitlines())
    return meta, body.strip()

def scan(directory: str) -> dict[str, dict]:
    skills = {}
    for path in Path(directory).glob("*/SKILL.md"):
        meta, _ = parse(path)
        skills[meta["name"]] = {"path": path, "description": meta["description"]}
    return skills

skills = scan("skills")
print(skills["weekly-report"]["description"])  # => 按团队模板写周报
```
```java no-run
record Skill(Path path, String description) {}

Map<String, Skill> scan(Path directory) throws IOException {
    var skills = new HashMap<String, Skill>();
    try (var folders = Files.list(directory)) {
        for (var folder : (Iterable<Path>) folders::iterator) {
            var path = folder.resolve("SKILL.md");
            if (!Files.exists(path)) {
                continue;
            }
            var meta = new HashMap<String, String>();
            var header = Files.readString(path).split("---\n", 3)[1];
            for (var line : header.strip().split("\n")) {
                var parts = line.split(": ", 2);
                meta.put(parts[0], parts[1]);
            }
            skills.put(meta.get("name"),
                new Skill(path, meta.get("description")));
        }
    }
    return skills;
}
```
```kotlin no-run
§ import java.io.File
data class Skill(val path: File, val description: String)

fun scan(directory: File): Map<String, Skill> =
    directory.listFiles().orEmpty()
        .map { File(it, "SKILL.md") }
        .filter { it.exists() }
        .associate { path ->
            val header = path.readText().split("---\n", limit = 3)[1]
            val meta = header.trim().lines().associate { line ->
                val (key, value) = line.split(": ", limit = 2)
                key to value
            }
            meta.getValue("name") to
                Skill(path, meta.getValue("description"))
        }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 遍历文件 | `Path.glob` | `Files.list` | `listFiles` |
| 读文本 | `read_text` | `Files.readString` | `readText` |
| 拆分 | `split("---\n", 2)` | `split("---\n", 3)` | `split("---\n", limit = 3)` |

> 要点: Python 的第二个参数是最多切几次，Java 和 Kotlin 是最多切成几段。这里用简单的字符串切分演示原理，正式项目用 YAML 解析库。
:::

接下来把元数据放进系统提示，再加一个工具。模型看到描述后，自己决定要不要读取。

```python
§ import pathlib
§ root = pathlib.Path("skills/weekly-report")
§ root.mkdir(parents=True)
§ (root / "SKILL.md").write_text("---\nname: weekly-report\ndescription: 按团队模板写周报\n---\n\n1. 读取模板\n", "utf-8")
§ from pathlib import Path
§ def parse(path):
§     _, header, body = path.read_text("utf-8").split("---\n", 2)
§     return dict(line.split(": ", 1) for line in header.strip().splitlines()), body.strip()
§ skills = {"weekly-report": {"path": root / "SKILL.md", "description": "按团队模板写周报"}}
def system_prompt(skills: dict[str, dict]) -> str:
    lines = [f"- {name}：{skill['description']}" for name, skill in skills.items()]
    return "你是助手。需要时用 load_skill 读取下面的技能：\n" + "\n".join(lines)

def load_skill(name: str) -> str:
    """读取一个技能的完整说明"""
    if name not in skills:
        return f"没有这个技能，可用的有 {list(skills)}"
    _, body = parse(skills[name]["path"])
    return body

print(system_prompt(skills))
print(load_skill("weekly-report"))
```
```output
你是助手。需要时用 load_skill 读取下面的技能：
- weekly-report：按团队模板写周报
1. 读取模板
```

加载之后，`SKILL.md` 里写的脚本和文件，由 Agent 用已有的工具去读取和运行。Skill 本身只是文字，不新增任何权限。

## Skill、工具和 MCP {#compare}

三者解决的问题不同，经常一起使用。

| 对比项 | 工具 | MCP | Skill |
| --- | --- | --- | --- |
| 提供什么 | 一个能执行的函数 | 一组工具的标准接入方式 | 做事的方法和步骤 |
| 形式 | 代码 | 协议和服务 | 文件夹和 Markdown |
| 上下文占用 | 定义一直占用 | 定义一直占用 | 平时只占描述 |
| 谁能编写 | 开发者 | 开发者 | 懂这件事的人都能写 |
| 适合 | 查询数据、执行操作 | 对接外部系统 | 团队流程、领域知识 |

判断方法：要让 Agent 能做一件以前做不到的事，加工具或 MCP。要让它把已经能做的事做得更好，写 Skill。

:::map Skill 概念对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| 元数据 | `@Tool` 的说明 | `AndroidManifest` 的声明 | 先让系统知道有这个能力 |
| 按需读取正文 | 类懒加载 | `by lazy` | 用到才占资源 |
| `scripts/` 里的脚本 | 工具类 | Gradle 任务 | 确定性的步骤写成代码 |
:::

## 写好 Skill {#writing}

- **`description` 决定会不会被用到。** 模型只看它来判断，要写清楚触发场景和关键词。「处理 PDF」太笼统，「提取 PDF 文字和表格、填写表单、合并文件，用户提到 PDF 时使用」才够具体。
- **写模型不知道的内容。** 团队规范、内部系统的用法、踩过的坑。通用知识不用写，模型本来就会。
- **确定的步骤写成脚本。** 有固定算法的事情，用脚本比让模型每次现写更可靠。
- **用真实任务测试。** 看模型能不能在该用的时候读取，读完能不能做对。

:::warn Skill 来源要可信
Skill 里的指令和脚本会以 Agent 的权限运行。恶意 Skill 可以让 Agent 泄露数据或执行危险命令。安装第三方 Skill 之前，要像审查代码一样读一遍。
:::

:::recap
- Skill 是带 `SKILL.md` 的文件夹，写着完成某类任务的方法
- 必填字段是 `name` 和 `description`，模型靠 `description` 决定是否使用
- 内容分三层按需加载，所以装很多个也不占上下文
- 自己实现时，把元数据放进系统提示，再提供一个读取工具
- 工具和 MCP 增加能力，Skill 传授方法
- 第三方 Skill 要先审查，它以 Agent 的权限运行
:::
