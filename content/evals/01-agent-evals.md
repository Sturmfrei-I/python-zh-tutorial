---
id: agent-evals
part: 评测
title: 评测指标
lede: 改了一句提示词，Agent 是变好了还是变差了？靠试几个例子看不出来。评测把这个问题变成一组能比较的数字。
source: 揭开 Agent 评测的面纱 | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents ; 构建有效的 Agent | https://www.anthropic.com/engineering/building-effective-agents ; OpenAI 评测最佳实践 | https://developers.openai.com/api/docs/guides/evaluation-best-practices
versions: Python 3.12 · Pydantic 2.14 · JUnit 6
seo_title: AI Agent 评测教程：评测指标、数据集和 Python 实现
seo_description: 讲解 AI Agent 怎么评测：和单元测试的区别、任务成功率、工具选择准确率、成本和延迟，怎么准备数据集，用 Python 实现评测程序，并和 JUnit 对比。
---

## 为什么要评测 {#why}

传统代码的行为是确定的，改完跑测试就知道对不对。Agent 不一样：

- 同样的输入，每次的结果可能不同
- 提示词改一句，可能修好一个问题，又弄坏另外三个
- 换模型或升级版本，行为会在你看不见的地方发生变化
- 结果的好坏经常没有唯一标准

不做评测的话，每次改动都只能试几个例子，凭感觉判断。评测就是一批固定的任务加一套打分方法，改动前后各跑一遍，看数字的变化。

| 对比项 | 单元测试 | 评测 |
| --- | --- | --- |
| 结果 | 通过或失败 | 一个分数或比例 |
| 通过标准 | 全部通过 | 不低于基线 |
| 运行成本 | 几乎免费 | 要花 token 和时间 |
| 确定性 | 每次相同 | 每次可能不同 |
| 失败时 | 修到通过 | 分析是否值得改 |

## 评什么 {#what}

Agent 要从三个层面看，越往后越接近用户的感受：

- **最终结果**：任务完成了吗？回答对吗？
- **过程**：工具选对了吗？步骤是否多余？
- **代价**：花了多少 token、多长时间？

看结果时，判断最终状态，不要过分要求具体路径。模型换一种方式完成了任务，一般也算对。退款 Agent 的评测应该检查订单是否真的退款了，而不是它调用工具的顺序。

## 准备数据集 {#dataset}

一条用例包括输入和判断标准。开始时不用很多，20 到 50 条来自真实场景的任务就够有用，之后不断增加。

用例要覆盖这几类：

- **常见任务**：用户最常做的事
- **边界情况**：信息不全、输入含糊
- **负面用例**：不该做的事，比如模型不应该调用退款工具的情况
- **踩过的坑**：线上出过问题的例子

```python
from pydantic import BaseModel, Field

class Case(BaseModel):
    id: str
    task: str
    expected_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    answer_contains: list[str] = Field(default_factory=list)

CASES = [
    Case(id="weather", task="北京天气", expected_tools=["get_weather"], answer_contains=["晴"]),
    Case(id="chat", task="你好", forbidden_tools=["get_weather"]),
]

CASES[0].expected_tools  # => ['get_weather']
```

## 运行和打分 {#run}

评测程序要记录 Agent 的每一步，再由打分函数判断。这里先用代码打分，能用代码判断的就不要用模型，这样又快又便宜，结果还是确定的。

:::compare 给一个用例打分
```python
from dataclasses import dataclass

@dataclass
class Trace:
    answer: str
    tools: list[str]
    tokens: int
    seconds: float

def grade(case: dict, trace: Trace) -> dict[str, bool]:
    return {
        "tools_ok": set(case["expected"]) <= set(trace.tools),
        "safe": not set(case["forbidden"]) & set(trace.tools),
        "answer_ok": all(text in trace.answer for text in case["contains"]),
    }

case = {"expected": ["get_weather"], "forbidden": [], "contains": ["晴"]}
trace = Trace("北京今天晴", ["get_weather"], 320, 1.2)

grade(case, trace)  # => {'tools_ok': True, 'safe': True, 'answer_ok': True}
```
```java
record Trace(String answer, List<String> tools) {}

record Case(List<String> expected, List<String> forbidden,
            List<String> contains) {}

Map<String, Boolean> grade(Case c, Trace t) {
    return new TreeMap<>(Map.of(
        "tools_ok", t.tools().containsAll(c.expected()),
        "safe", Collections.disjoint(t.tools(), c.forbidden()),
        "answer_ok", c.contains().stream().allMatch(t.answer()::contains)
    ));
}

var c = new Case(List.of("get_weather"), List.of(), List.of("晴"));
var t = new Trace("北京今天晴", List.of("get_weather"));
System.out.println(grade(c, t));  // => {answer_ok=true, safe=true, tools_ok=true}
```
```kotlin
data class Trace(val answer: String, val tools: List<String>)

data class Case(
    val expected: List<String>,
    val forbidden: List<String>,
    val contains: List<String>,
)

fun grade(c: Case, t: Trace) = mapOf(
    "tools_ok" to t.tools.containsAll(c.expected),
    "safe" to t.tools.intersect(c.forbidden.toSet()).isEmpty(),
    "answer_ok" to c.contains.all { it in t.answer },
)

val c = Case(listOf("get_weather"), emptyList(), listOf("晴"))
val t = Trace("北京今天晴", listOf("get_weather"))
println(grade(c, t))  // => {tools_ok=true, safe=true, answer_ok=true}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 记录数据 | `dataclass` | `record` | `data class` |
| 子集判断 | `set(a) <= set(b)` | `containsAll` | `containsAll` |
| 交集为空 | `not a & b` | `Collections.disjoint` | `intersect().isEmpty()` |
| 全部满足 | `all()` | `allMatch` | `all` |

> 要点: 打分函数只返回结果，不做断言。评测要的是汇总之后的比例，一条失败不应该中断整批运行。
:::

## 常用指标 {#metrics}

把所有用例的结果汇总成几个数字：

| 指标 | 含义 | 关注什么 |
| --- | --- | --- |
| 任务成功率 | 成功的用例占比 | 最重要的一个数字 |
| 工具选择准确率 | 工具用对的比例 | Agent 判断得对不对 |
| 平均步数 | 完成任务调用了几轮模型 | 步数越少越省钱 |
| 平均 token | 每个任务的消耗 | 费用 |
| P95 延迟 | 95% 的任务在多长时间内完成 | 用户的等待时间 |

延迟要看 P95，不要只看平均值。平均值会被大量快速请求掩盖，少数用户等待几分钟的情况看不出来。

```python
import statistics

results = [
    {"success": True, "tokens": 800, "seconds": 2.1},
    {"success": True, "tokens": 1200, "seconds": 3.4},
    {"success": False, "tokens": 5000, "seconds": 18.0},
    {"success": True, "tokens": 900, "seconds": 2.5},
]

def summarize(results: list[dict]) -> dict:
    seconds = [r["seconds"] for r in results]
    return {
        "success_rate": sum(r["success"] for r in results) / len(results),
        "avg_tokens": statistics.mean(r["tokens"] for r in results),
        "p95_seconds": round(statistics.quantiles(seconds, n=20, method="inclusive")[-1], 1),
    }

summarize(results)  # => {'success_rate': 0.75, 'avg_tokens': 1975, 'p95_seconds': 15.8}
```

用例少时，几个点的变化可能只是随机波动。50 条用例里多对一条就是 2%，不要对这样的差距太敏感。

## 线上指标 {#online}

离线评测只覆盖你想到的情况。上线后还要看这些数字，它们能发现数据集里没有的问题：

- 用户点赞和点踩的比例
- 用户重新提问或中途放弃的比例
- 转人工的比例
- 工具报错率，每个任务的费用

把线上的失败案例加进数据集，评测就会越来越贴近真实使用。下一章讲结果没法用代码判断时怎么办。

:::map 评测概念对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| 评测程序 | JUnit 测试 | JUnit 测试 | 评测输出比例，不是通过或失败 |
| `@dataclass Trace` | `record` | `data class` | 记录一次运行 |
| `statistics.quantiles` | Micrometer 的百分位 | Micrometer 的百分位 | 计算 P95 |
| 基线分数 | 性能基线 | Macrobenchmark 基线 | 和上一次比较 |
:::

:::recap
- Agent 的行为不确定，改动的影响要靠评测判断，不能靠感觉
- 评测的结果是比例，通过标准是不低于基线
- 从结果、过程和代价三个层面看，优先检查最终状态
- 数据集从 20 到 50 条真实任务开始，要包含不该做的事
- 能用代码打分的就用代码，打分函数只返回结果，不做断言
- 看成功率、token 和 P95 延迟，并把线上失败加回数据集
:::
