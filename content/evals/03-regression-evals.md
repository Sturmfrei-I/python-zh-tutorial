---
id: regression-evals
part: 评测
title: 回归场景集
lede: 把出过问题的场景固定下来，每次改动都跑一遍，修好的问题才不会再回来。这一章用 pytest 搭一套能进 CI 的回归评测。
source: 揭开 Agent 评测的面纱 | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents ; pytest 参数化 | https://docs.pytest.org/en/stable/how-to/parametrize.html ; OpenAI 评测最佳实践 | https://developers.openai.com/api/docs/guides/evaluation-best-practices
versions: pytest 9.2 · OpenAI Python SDK 3.42 · JUnit 6
seo_title: Agent 回归测试教程：用 pytest 搭建回归场景集
seo_description: 讲解 Agent 回归评测：用 pytest 参数化管理场景、假模型和真实模型两层测试、多次运行取通过率、基线比较和接入 CI，并和 JUnit 参数化测试对比。
---

## 回归场景集是什么 {#what}

「评测指标」一章的评测用来判断整体水平。回归场景集是其中要求最严的一部分：这些任务已经做对了，以后也必须做对。

场景主要来自三个地方：线上的失败案例、修过的 bug、绝对不能出错的业务，比如不能给错误的用户退款。

一个 bug 的处理流程应该是这样：先把它写成场景，确认场景失败，修好后确认通过，再把它永远留在集合里。

## 分两层测试 {#layers}

每次提交都调用真实模型又慢又贵，所以测试分成两层：

| 对比项 | 确定性测试 | 真实模型评测 |
| --- | --- | --- |
| 模型 | 假模型，按脚本返回 | 真实模型 |
| 测什么 | 循环、工具执行、错误处理 | 模型的判断 |
| 费用 | 免费 | 要花钱 |
| 运行时机 | 每次提交 | 每天，或改动提示词时 |
| 结果 | 必须全部通过 | 看通过率 |

假模型按顺序返回写好的回答，用来验证你自己的代码：工具出错时循环有没有继续，达到步数上限时有没有停止。

:::compare 用假模型测试循环
```python
import pytest

class FakeModel:
    def __init__(self, replies: list[dict]):
        self.replies = replies

    def complete(self, messages: list[dict]) -> dict:
        return self.replies.pop(0)

def run_agent(model: FakeModel, tools: dict, task: str, max_steps: int = 3) -> str:
    messages = [{"role": "user", "content": task}]
    for _ in range(max_steps):
        reply = model.complete(messages)
        if "tool" not in reply:
            return reply["text"]
        messages.append({"role": "tool", "content": tools[reply["tool"]]()})
    raise RuntimeError("超过最大步数")

def test_runs_tool_then_answers():
    model = FakeModel([{"tool": "search"}, {"text": "完成"}])
    assert run_agent(model, {"search": lambda: "结果"}, "查一下") == "完成"

def test_stops_at_max_steps():
    model = FakeModel([{"tool": "search"}] * 5)
    with pytest.raises(RuntimeError, match="最大步数"):
        run_agent(model, {"search": lambda: "结果"}, "查一下")
§ if __name__ == "__main__":
§     assert pytest.main(["-q", "-p", "no:cacheprovider", "snippet.py"]) == 0
```
```java no-run
interface Model {
    String complete(List<String> messages);
}

String runAgent(Model model, int maxSteps) {
    var messages = new ArrayList<String>();
    for (var i = 0; i < maxSteps; i++) {
        var reply = model.complete(messages);
        if (!reply.startsWith("tool:")) {
            return reply;
        }
        messages.add("结果");
    }
    throw new IllegalStateException("超过最大步数");
}

@Test
void stopsAtMaxSteps() {
    var model = mock(Model.class);
    when(model.complete(anyList())).thenReturn("tool:search");

    assertThrows(IllegalStateException.class, () -> runAgent(model, 3));
    verify(model, times(3)).complete(anyList());
}
```
```kotlin no-run
interface Model {
    fun complete(messages: List<String>): String
}

fun runAgent(model: Model, maxSteps: Int): String {
    val messages = mutableListOf<String>()
    repeat(maxSteps) {
        val reply = model.complete(messages)
        if (!reply.startsWith("tool:")) return reply
        messages += "结果"
    }
    error("超过最大步数")
}

@Test
fun stopsAtMaxSteps() {
    val model = mockk<Model>()
    every { model.complete(any()) } returns "tool:search"

    assertFailsWith<IllegalStateException> { runAgent(model, 3) }
    verify(exactly = 3) { model.complete(any()) }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 假模型 | 自己写一个小类 | Mockito | MockK |
| 依赖注入 | 作为参数传入 | 作为参数传入 | 作为参数传入 |
| 验证次数 | 看 `replies` 剩余数量 | `verify(times(3))` | `verify(exactly = 3)` |

> 要点: 模型调用要作为依赖传进循环，才能换成假模型。把 `client` 写死在函数里的话，这种测试就写不了。
:::

## 场景写成数据 {#scenarios}

真实模型这一层，把场景写成 JSON 或 YAML，产品同事也能看懂和添加。代码只负责读取和判断。

```json
[
  {
    "id": "refund-basic",
    "task": "订单 123 我不想要了",
    "must_call": ["refund"],
    "must_not_call": ["delete_account"],
    "source": "线上问题 2026-09"
  },
  {
    "id": "no-refund-for-chat",
    "task": "你们的退款政策是什么？",
    "must_call": [],
    "must_not_call": ["refund"],
    "source": "线上问题 2026-10"
  }
]
```

每个场景一个测试，失败时能直接看到是哪个场景。`source` 字段记录来源，以后才知道为什么有这条场景。

:::compare 按场景参数化
```python
import json
import pathlib

import pytest

§ pathlib.Path("scenarios.json").write_text(json.dumps([
§     {"id": "refund-basic", "task": "订单 123 我不想要了", "must_call": ["refund"], "must_not_call": ["delete_account"]},
§     {"id": "no-refund-for-chat", "task": "退款政策是什么", "must_call": [], "must_not_call": ["refund"]},
§ ]), "utf-8")
SCENARIOS = json.loads(pathlib.Path("scenarios.json").read_text("utf-8"))

def run_agent(task: str) -> list[str]:
    """运行 Agent，返回调用过的工具"""
    return ["refund"] if "订单" in task else []

@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["id"])
def test_scenario(scenario: dict):
    tools = run_agent(scenario["task"])
    assert set(scenario["must_call"]) <= set(tools)
    assert not set(scenario["must_not_call"]) & set(tools)
§ if __name__ == "__main__":
§     assert pytest.main(["-q", "-p", "no:cacheprovider", "snippet.py"]) == 0
```
```java no-run
record Scenario(String id, String task, List<String> mustCall,
                List<String> mustNotCall) {}

static Stream<Scenario> scenarios() {
    return Stream.of(new Scenario("refund-basic", "订单 123 我不想要了",
        List.of("refund"), List.of("delete_account")));
}

@ParameterizedTest
@MethodSource("scenarios")
void scenario(Scenario scenario) {
    var tools = runAgent(scenario.task());
    assertTrue(tools.containsAll(scenario.mustCall()));
    assertTrue(Collections.disjoint(tools, scenario.mustNotCall()));
}
§ List<String> runAgent(String task) { return List.of(); }
```
```kotlin no-run
data class Scenario(
    val id: String,
    val task: String,
    val mustCall: List<String>,
    val mustNotCall: List<String>,
)

class ScenarioTest {
    @ParameterizedTest
    @MethodSource("scenarios")
    fun scenario(scenario: Scenario) {
        val tools = runAgent(scenario.task)
        assertTrue(tools.containsAll(scenario.mustCall))
        assertTrue(tools.intersect(scenario.mustNotCall.toSet()).isEmpty())
    }

    companion object {
        @JvmStatic
        fun scenarios() = listOf(
            Scenario(
                "refund-basic",
                "订单 123 我不想要了",
                listOf("refund"),
                listOf("delete_account"),
            ),
        )
    }
}
§ fun runAgent(task: String): List<String> = emptyList()
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 数据来源 | 任意列表 | `@MethodSource` | `@MethodSource` |
| 测试名 | `ids` 参数 | `@ParameterizedTest(name = ...)` | `@ParameterizedTest(name = ...)` |
| 数据写法 | 读 JSON 文件 | 读文件或写在代码里 | 读文件或写在代码里 |

> 要点: `ids` 让失败信息显示场景名，而不是一个序号。
:::

调用真实模型的测试用 `pytest.mark` 分开，平时不运行：

```bash
pytest -m "not llm"     # 每次提交运行
pytest -m llm           # 每天或改动提示词时运行
```

## 处理不确定性 {#flaky}

模型的结果不是每次相同，一次失败可能只是运气不好，一次通过也可能只是运气好。重要的场景要跑多次，看通过率。

```python
from collections.abc import Callable

def pass_rate(scenario: dict, run: Callable[[dict], bool], times: int = 5) -> float:
    return sum(run(scenario) for _ in range(times)) / times

results = iter([True, True, False, True, True])
rate = pass_rate({"id": "refund"}, lambda s: next(results))

print(rate)  # => 0.8
```

不同的场景要求不同：

- **安全类场景**：要求 100%。比如「绝不能退款给别人」，有一次失败就要处理。
- **普通场景**：设一个门槛，比如 5 次里至少 4 次通过。

不要用自动重试掩盖不稳定。通过率下降说明提示词的约束不够，要去改提示词或工具。

## 和基线比较 {#baseline}

每次运行的结果存成一个文件，提交进仓库。新结果和它比较，只有变差才算失败。这样不用要求所有场景都通过，又能挡住退步。

```python
def compare(baseline: dict[str, float], current: dict[str, float], tolerance: float = 0.1) -> list[str]:
    regressions = []
    for name, score in baseline.items():
        if current.get(name, 0.0) < score - tolerance:
            regressions.append(f"{name}: {score} -> {current.get(name, 0.0)}")
    return regressions

baseline = {"refund-basic": 1.0, "address-change": 0.8, "faq": 0.6}
current = {"refund-basic": 0.6, "address-change": 0.8, "faq": 0.8}

compare(baseline, current)  # => ['refund-basic: 1.0 -> 0.6']
```

`faq` 的分数上升了，`refund-basic` 下降了，只看总分会发现平均分几乎没变。所以要逐个场景比较，不能只看平均值。

## 接入 CI {#ci}

- **每次提交**：运行假模型测试，几秒钟完成。
- **改动提示词或工具的 PR**：运行回归场景，把分数变化贴到 PR 里。
- **每天定时**：完整运行一遍，发现模型服务端的变化。模型就算没有换名字，行为也可能悄悄变化。

提示词要和代码一起进版本管理。这样才能知道分数变化是哪次提交带来的，需要时也能回滚。

运行之前估算费用，设置预算上限。场景数量乘以运行次数，再乘以每次的 token，很容易比想象中贵。

:::map 回归测试写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `@pytest.mark.parametrize` | `@ParameterizedTest` | `@ParameterizedTest` | 每个场景一个测试 |
| `pytest.mark.llm` | `@Tag("llm")` | `@Tag("llm")` | 把昂贵的测试分开 |
| `pytest -m "not llm"` | Gradle 的 `excludeTags` | Gradle 的 `excludeTags` | 平时不运行 |
| 假模型类 | Mockito | MockK | 不访问真实接口 |
| 基线文件 | 快照测试 | Compose 截图测试 | 只有变差才算失败 |
:::

:::recap
- 回归场景集固定已经做对的任务，每个线上 bug 都要变成一条场景
- 假模型测试循环和错误处理，每次提交都运行，真实模型的评测单独运行
- 场景写成数据，每个场景一个测试，记录来源
- 模型结果不确定，重要场景跑多次看通过率，安全类场景要求 100%
- 和基线比较时逐个场景看，不能只看平均分
- 提示词进版本管理，定时运行以发现服务端模型的变化
:::
