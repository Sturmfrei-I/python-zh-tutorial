---
id: react-plan-execute
part: Agent 基础
title: ReAct 和先规划后执行
lede: 边想边做，还是想好再做？这是 Agent 最基本的两种组织方式。这一章把它们都实现一遍，再看什么时候根本不需要 Agent。
source: ReAct 论文 | https://arxiv.org/abs/2210.03629 ; 构建有效的 Agent | https://www.anthropic.com/engineering/building-effective-agents ; LangGraph 工作流和 Agent | https://docs.langchain.com/oss/python/langgraph/workflows-agents
versions: OpenAI Python SDK 3.42 · Pydantic 2.14
seo_title: ReAct 和 Plan-and-Execute：Agent 开发的两种模式
seo_description: Agent 开发的两种基本模式：ReAct 的思考、行动、观察循环和先规划后执行，用 Python 实现，并介绍提示链、路由、并行、编排和评估优化五种工作流模式。
---

## ReAct {#react}

ReAct 来自 2022 年的论文，名字是 Reasoning 和 Acting 的组合。它让模型交替进行三件事：

- **Thought**：想一想现在知道什么，下一步该做什么
- **Action**：调用一个工具
- **Observation**：读取工具返回的结果

上一章的循环其实就是 ReAct。论文发表时还没有 Function Calling，模型只能输出文字，所以程序要自己解析。这段代码能看清它的原理。

```python
§ import fakellm
§ fakellm.serve(
§     "Thought: 要先查天气\nAction: get_weather[北京]",
§     "Thought: 知道天气了\nAnswer: 北京今天晴",
§ )
§ MODEL = "demo"
import re

from openai import OpenAI

client = OpenAI()

PROMPT = """按这个格式回答：
Thought: 你的思考
Action: 工具名[参数]
工具返回后你会收到 Observation。得出结论时输出 Answer: 最终回答。
可用工具：get_weather[城市]"""

TOOLS = {"get_weather": lambda city: f"{city}：晴"}

def react(task: str) -> str:
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": task},
    ]
    for _ in range(5):
        response = client.chat.completions.create(model=MODEL, messages=messages)
        text = response.choices[0].message.content
        messages.append({"role": "assistant", "content": text})

        if match := re.search(r"Answer: (.*)", text):
            return match.group(1)

        name, argument = re.search(r"Action: (\w+)\[(.*)\]", text).groups()
        observation = TOOLS[name](argument)
        messages.append({"role": "user", "content": f"Observation: {observation}"})
    raise RuntimeError("超过最大步数")

print(react("北京今天天气如何？"))  # => 北京今天晴
```

现在不用这样解析文字了，`tool_calls` 比正则可靠得多，而且新模型自带思考能力。这种写法只在模型不支持工具调用时才有用。ReAct 留下来的是思路：每次只决定下一步，根据结果再决定再下一步。

## ReAct 的优缺点 {#tradeoffs}

ReAct 适合下一步取决于上一步结果的任务，比如调试程序、查资料。它能随时调整，遇到意外情况也能应对。

它的缺点也来自「走一步看一步」：

- 容易陷入局部，做很多无关的步骤
- 任务复杂时会忘记整体目标
- 每一步都要调用模型，累积的历史让费用增长很快

## 先规划后执行 {#plan}

另一种做法是把思考和行动分开。先让模型列出完整的计划，再逐步执行，每一步可以用更便宜的模型，只拿到这一步需要的上下文。

计划用结构化输出，程序才能读取每一步。

:::compare 计划的数据结构
```python
§ import fakellm
§ fakellm.serve('{"goal": "写报告", "steps": [{"id": 1, "task": "收集数据", "depends_on": []}, {"id": 2, "task": "写总结", "depends_on": [1]}]}')
§ MODEL = "demo"
from openai import OpenAI
from pydantic import BaseModel, Field

class Step(BaseModel):
    id: int
    task: str = Field(description="这一步要完成的事")
    depends_on: list[int] = Field(description="依赖的步骤编号")

class Plan(BaseModel):
    goal: str
    steps: list[Step]

client = OpenAI()

def make_plan(task: str) -> Plan:
    response = client.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": "把任务拆成三到七个步骤"},
            {"role": "user", "content": task},
        ],
        response_format=Plan,
    )
    return response.choices[0].message.parsed

plan = make_plan("写一份销售报告")
[step.task for step in plan.steps]  # => ['收集数据', '写总结']
```
```java no-run
record Step(int id, String task, List<Integer> dependsOn) {}

record Plan(String goal, List<Step> steps) {}

interface Planner {
    @SystemMessage("把任务拆成三到七个步骤")
    Plan makePlan(String task);
}

Plan run(ChatModel model) {
    var planner = AiServices.create(Planner.class, model);
    return planner.makePlan("写一份销售报告");
}
```
```kotlin no-run
data class Step(val id: Int, val task: String, val dependsOn: List<Int>)

data class Plan(val goal: String, val steps: List<Step>)

interface Planner {
    @SystemMessage("把任务拆成三到七个步骤")
    fun makePlan(task: String): Plan
}

fun run(model: ChatModel): Plan {
    val planner = AiServices.create(Planner::class.java, model)
    return planner.makePlan("写一份销售报告")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 结构 | Pydantic 模型 | `record` | `data class` |
| 调用 | `parse` | 接口方法返回 `Plan` | 接口方法返回 `Plan` |
| 校验 | Pydantic | Jackson 反序列化 | Jackson 反序列化 |

> 要点: `depends_on` 把计划变成依赖图，没有依赖关系的步骤可以并行执行。
:::

执行时按顺序处理，每一步只拿到前面步骤的结果，不带上全部历史。

```python
§ import fakellm
§ fakellm.serve("数据：销量增长 10%", "总结：销量增长良好")
§ MODEL = "demo"
§ from openai import OpenAI
§ from pydantic import BaseModel
§ client = OpenAI()
§ class Step(BaseModel):
§     id: int
§     task: str
§     depends_on: list[int]
§ class Plan(BaseModel):
§     goal: str
§     steps: list[Step]
§ plan = Plan(goal="写报告", steps=[Step(id=1, task="收集数据", depends_on=[]), Step(id=2, task="写总结", depends_on=[1])])
def execute_plan(plan: Plan) -> dict[int, str]:
    results: dict[int, str] = {}
    for step in plan.steps:
        context = "\n".join(results[i] for i in step.depends_on)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"总目标：{plan.goal}。只完成当前步骤。"},
                {"role": "user", "content": f"已有结果：\n{context}\n\n当前步骤：{step.task}"},
            ],
        )
        results[step.id] = response.choices[0].message.content
    return results

execute_plan(plan)[2]  # => '总结：销量增长良好'
```

计划可能赶不上变化。实际项目里常加一步重新规划：每执行完一步，检查结果和计划是否还相符，不符合就调整剩下的步骤。这部分用 LangGraph 写起来很方便，后面会讲。

## 两种方式怎么选 {#choose}

| 对比项 | ReAct | 先规划后执行 |
| --- | --- | --- |
| 适合的任务 | 探索性的，步骤取决于中间结果 | 目标明确，能预先拆解 |
| 灵活性 | 高，每步都能调整 | 低，要靠重新规划 |
| 费用 | 历史一直累积 | 步骤之间上下文较小 |
| 过程是否可见 | 边做边看 | 执行前就能看到计划 |
| 人工审批 | 逐步确认 | 确认一次计划 |

两者经常组合使用：外层规划，内层每个步骤是一个小的 ReAct 循环。

## 可能不需要 Agent {#workflows}

很多任务用固定的流程就能完成，更便宜，也更容易测试。Anthropic 总结了五种常见的工作流模式：

| 模式 | 做法 | 例子 |
| --- | --- | --- |
| 提示链 | 上一步的输出作为下一步的输入 | 写大纲，再写全文 |
| 路由 | 先分类，再交给对应的处理流程 | 客服请求按类型分流 |
| 并行 | 同时做多件事，再合并结果 | 多个维度审查同一段代码 |
| 编排者和执行者 | 一个模型拆任务，多个模型分别执行 | 修改多个文件 |
| 评估优化 | 一个模型生成，另一个评价，循环改进 | 翻译润色 |

路由是最常用的，用结构化输出做分类，后面就是普通的 `if`。

:::compare 路由
```python
§ import fakellm
§ fakellm.serve('{"category": "refund"}')
§ MODEL = "demo"
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel

class Route(BaseModel):
    category: Literal["refund", "shipping", "other"]

client = OpenAI()

def classify(text: str) -> str:
    response = client.chat.completions.parse(
        model=MODEL,
        messages=[{"role": "user", "content": text}],
        response_format=Route,
    )
    return response.choices[0].message.parsed.category

def handle(text: str) -> str:
    match classify(text):
        case "refund":
            return "转到退款流程"
        case "shipping":
            return "转到物流查询"
        case _:
            return "转人工"

print(handle("我想退货"))  # => 转到退款流程
```
```java no-run
enum Category { REFUND, SHIPPING, OTHER }

interface Router {
    @UserMessage("判断这个请求的类别：{{it}}")
    Category classify(String text);
}

String handle(Router router, String text) {
    return switch (router.classify(text)) {
        case REFUND -> "转到退款流程";
        case SHIPPING -> "转到物流查询";
        case OTHER -> "转人工";
    };
}
```
```kotlin no-run
enum class Category { REFUND, SHIPPING, OTHER }

interface Router {
    @UserMessage("判断这个请求的类别：{{it}}")
    fun classify(text: String): Category
}

fun handle(router: Router, text: String) = when (router.classify(text)) {
    Category.REFUND -> "转到退款流程"
    Category.SHIPPING -> "转到物流查询"
    Category.OTHER -> "转人工"
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 类别 | `Literal` | `enum` | `enum class` |
| 分支 | `match` | `switch` | `when` |
| 完整性检查 | 类型检查工具才会提示 | 编译器检查 | 编译器检查 |

> 要点: 路由之后的分支都是确定的代码，能用普通测试覆盖。模型只负责分类这一步。
:::

:::recap
- ReAct 交替思考、行动和观察，上一章的循环就是它的现代写法
- 走一步看一步很灵活，但费用高，也容易偏离目标
- 先规划后执行：结构化输出计划，每步只带需要的上下文，必要时重新规划
- 探索性任务用 ReAct，目标明确的任务用规划，两者可以组合
- 优先考虑提示链、路由、并行这些工作流，确实需要时才用 Agent
:::
