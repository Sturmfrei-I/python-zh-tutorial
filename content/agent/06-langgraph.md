---
id: langgraph
part: 连接外部能力
title: LangGraph
lede: 循环写到一定规模，要加断点续跑、人工审批和分支时，手写的 while 就开始难维护了。LangGraph 把 Agent 写成状态图，这些能力都是现成的。
source: LangGraph 概览 | https://docs.langchain.com/oss/python/langgraph/overview ; 快速开始 | https://docs.langchain.com/oss/python/langgraph/quickstart ; 持久化 | https://docs.langchain.com/oss/python/langgraph/persistence ; 中断 | https://docs.langchain.com/oss/python/langgraph/interrupts
versions: LangGraph 1.2 · OpenAI Python SDK 3.42
seo_title: LangGraph 教程：用状态图开发可恢复的 AI Agent
seo_description: 用 LangGraph 开发 AI Agent 智能体：State、Node、Edge、条件边和循环，用 checkpointer 持久化和恢复，用 interrupt 实现人工审批，并和 Java、Kotlin 状态机写法对比。
---

## 什么时候用 {#when}

「工具调用循环」一章的 Agent 只有几十行，简单任务这样写就够了。下面这些需求出现时，再考虑 LangGraph：

- 任务要跑很久，进程重启后能从中断的地方继续
- 中途要停下来等人审批，可能等几小时
- 流程有多个分支和循环，写在一个函数里已经很难读
- 想回看每一步的状态，或者从某一步重新运行

LangGraph 不依赖特定的模型。下面的例子直接调用 OpenAI SDK，也不需要安装 LangChain 的模型封装。

```bash
pip install langgraph
```

## 状态、节点和边 {#concepts}

LangGraph 把程序写成一张图，有三个概念：

- **State**：贯穿全程的数据，一个 `TypedDict`
- **Node**：普通函数，读取状态，返回要更新的字段
- **Edge**：决定下一步运行哪个节点

字段默认用新值覆盖旧值。列表要累加时，用 `Annotated` 指定合并函数，`operator.add` 就是列表拼接。

:::compare 状态机
```python
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

class State(TypedDict):
    logs: Annotated[list[str], operator.add]
    count: int

def step(state: State) -> dict:
    return {"logs": [f"第 {state['count']} 次"], "count": state["count"] + 1}

def route(state: State) -> str:
    return "step" if state["count"] < 3 else END

builder = StateGraph(State)
builder.add_node("step", step)
builder.add_edge(START, "step")
builder.add_conditional_edges("step", route, ["step", END])
graph = builder.compile()

result = graph.invoke({"logs": [], "count": 1})
print(result["logs"])  # => ['第 1 次', '第 2 次']
```
```java
enum Node { STEP, END }

record State(List<String> logs, int count) {}

State step(State state) {
    var logs = new ArrayList<>(state.logs());
    logs.add("第 " + state.count() + " 次");
    return new State(logs, state.count() + 1);
}

Node route(State state) {
    return state.count() < 3 ? Node.STEP : Node.END;
}

var state = new State(List.of(), 1);
var node = Node.STEP;
while (node != Node.END) {
    state = step(state);
    node = route(state);
}
System.out.println(state.logs());  // => [第 1 次, 第 2 次]
```
```kotlin
data class State(val logs: List<String>, val count: Int)

fun step(state: State) = state.copy(
    logs = state.logs + "第 ${state.count} 次",
    count = state.count + 1,
)

tailrec fun run(state: State): State {
    val next = step(state)
    return if (next.count < 3) run(next) else next
}

println(run(State(emptyList(), 1)).logs)  // => [第 1 次, 第 2 次]
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 状态 | `TypedDict` | `record` | `data class` |
| 节点 | 返回要更新的字段 | 返回新状态 | 返回新状态 |
| 路由 | `add_conditional_edges` | 循环里判断 | 递归或 `when` |
| 持久化和恢复 | 框架提供 | 自己实现 | 自己实现 |

> 要点: 图的本质就是一个状态机。写过 Navigation 图或 MVI 的话，会觉得很熟悉，LangGraph 多出来的价值在持久化和中断。
:::

## 用图写 Agent {#agent}

工具调用循环可以画成两个节点：`model` 调用模型，`tools` 执行工具，条件边决定是继续还是结束。

```python
§ import fakellm
§ fakellm.serve(fakellm.tool("get_weather", city="北京"), "北京今天晴")
§ MODEL = "demo"
§ SCHEMAS = [{"type": "function", "function": {"name": "get_weather", "parameters": {"type": "object"}}}]
import json
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

client = OpenAI()
TOOLS = {"get_weather": lambda city: f"{city}：晴"}

class State(TypedDict):
    messages: Annotated[list[dict], operator.add]

def call_model(state: State) -> dict:
    response = client.chat.completions.create(
        model=MODEL, messages=state["messages"], tools=SCHEMAS,
    )
    return {"messages": [response.choices[0].message.model_dump(exclude_none=True)]}

def call_tools(state: State) -> dict:
    results = []
    for call in state["messages"][-1]["tool_calls"]:
        function = call["function"]
        output = TOOLS[function["name"]](**json.loads(function["arguments"]))
        results.append({"role": "tool", "tool_call_id": call["id"], "content": output})
    return {"messages": results}

def should_continue(state: State) -> str:
    return "tools" if state["messages"][-1].get("tool_calls") else END

builder = StateGraph(State)
builder.add_node("model", call_model)
builder.add_node("tools", call_tools)
builder.add_edge(START, "model")
builder.add_conditional_edges("model", should_continue, ["tools", END])
builder.add_edge("tools", "model")
graph = builder.compile()

result = graph.invoke({"messages": [{"role": "user", "content": "北京天气？"}]})
print(result["messages"][-1]["content"])  # => 北京今天晴
```

`graph.get_graph().draw_mermaid()` 能输出流程图的 Mermaid 代码，流程复杂时用来检查结构。

循环的保险要自己设。LangGraph 默认的步数上限很大，这个版本是 10007 步，调用时用 `recursion_limit` 设一个合理的值，超过后抛 `GraphRecursionError`。

```python
§ from typing import TypedDict
§ from langgraph.errors import GraphRecursionError
§ from langgraph.graph import START, StateGraph
§ class Loop(TypedDict):
§     count: int
§ loop = StateGraph(Loop)
§ loop.add_node("step", lambda state: {"count": state["count"] + 1})
§ loop.add_edge(START, "step")
§ loop.add_edge("step", "step")
§ graph = loop.compile()
try:
    graph.invoke({"count": 0}, config={"recursion_limit": 25})
except GraphRecursionError:
    print("超过步数上限")  # => 超过步数上限
```

## 持久化 {#persistence}

编译时传入 checkpointer，每运行完一个节点就保存一次状态。用 `thread_id` 区分会话，同一个 `thread_id` 再次调用时，会接着之前的状态继续。

```python
import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

class State(TypedDict):
    messages: Annotated[list[str], operator.add]

def reply(state: State) -> dict:
    return {"messages": [f"收到 {len(state['messages'])} 条"]}

builder = StateGraph(State)
builder.add_node("reply", reply)
builder.add_edge(START, "reply")
builder.add_edge("reply", END)
graph = builder.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "ada"}}

graph.invoke({"messages": ["你好"]}, config)
result = graph.invoke({"messages": ["在吗"]}, config)
print(result["messages"])  # => ['你好', '收到 1 条', '在吗', '收到 3 条']

print(len(graph.invoke({"messages": ["你好"]}, {"configurable": {"thread_id": "bob"}})["messages"]))  # => 2
```

`InMemorySaver` 只存在内存里，适合开发和测试。线上要换成 `langgraph-checkpoint-sqlite` 或 `langgraph-checkpoint-postgres` 这类存数据库的版本，换的时候其他代码都不用改。

## 人工审批 {#interrupt}

节点里调用 `interrupt` 会暂停整个图，状态保存到 checkpointer，程序可以直接结束。等用户操作后，用 `Command(resume=值)` 继续，这个值就是 `interrupt` 的返回值。

这就是持久化最大的用处：审批可以等几天，服务重启过也没关系。

```python
import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

class State(TypedDict):
    logs: Annotated[list[str], operator.add]

def send_email(state: State) -> dict:
    approved = interrupt({"action": "发送邮件", "to": "boss@example.com"})
    return {"logs": ["已发送" if approved else "已取消"]}

builder = StateGraph(State)
builder.add_node("send_email", send_email)
builder.add_edge(START, "send_email")
builder.add_edge("send_email", END)
graph = builder.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "task-1"}}

result = graph.invoke({"logs": []}, config)
print(result["__interrupt__"][0].value["action"])  # => 发送邮件
print(graph.get_state(config).next)  # => ('send_email',)

result = graph.invoke(Command(resume=True), config)
print(result["logs"])  # => ['已发送']
```

:::warn 恢复时节点从头运行
恢复后，`interrupt` 所在的节点会从第一行重新运行，而不是从 `interrupt` 那一行继续。所以 `interrupt` 之前不要放有副作用的代码，否则扣款、发邮件这类操作会执行两次。
:::

## 流式输出 {#stream}

`graph.stream` 在运行时逐步产出结果。`stream_mode="updates"` 每次产出一个节点的更新，用来向前端显示进度。

```python
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

class State(TypedDict):
    logs: Annotated[list[str], operator.add]

builder = StateGraph(State)
builder.add_node("search", lambda state: {"logs": ["搜索完成"]})
builder.add_node("write", lambda state: {"logs": ["写作完成"]})
builder.add_edge(START, "search")
builder.add_edge("search", "write")
builder.add_edge("write", END)
graph = builder.compile()

for event in graph.stream({"logs": []}, stream_mode="updates"):
    print(event)
```
```output
{'search': {'logs': ['搜索完成']}}
{'write': {'logs': ['写作完成']}}
```

在 FastAPI 里用 `astream`，它是异步生成器，可以直接接到 SSE 接口上。

:::map LangGraph 概念对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `StateGraph` | Spring Statemachine | Navigation 图 | 都在描述状态怎么流转 |
| `State` | `record` | `UiState` | 贯穿全程的数据 |
| 节点函数 | 状态机的动作 | MVI 的 reducer | 输入状态，输出变化 |
| `checkpointer` | Spring Batch 的 `JobRepository` | `SavedStateHandle` | 保存进度，可以恢复 |
| `interrupt` | 人工审批步骤 | 等待用户操作 | 暂停后可以恢复 |
| `thread_id` | 业务流水号 | `NavBackStackEntry` | 区分不同的运行实例 |
:::

:::recap
- 简单任务手写循环就够，要持久化、审批和复杂分支时再用 LangGraph
- State 是数据，Node 是函数，Edge 决定下一步，条件边实现循环
- 列表字段用 `Annotated` 指定合并方式，否则新值会覆盖旧值
- checkpointer 按 `thread_id` 保存状态，线上要用数据库版本
- `interrupt` 暂停，`Command(resume=...)` 恢复，节点会从头重新运行
- `stream` 和 `astream` 逐步产出结果，方便接到 SSE
:::
