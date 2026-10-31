---
id: agent-loop
part: Agent 基础
title: 工具调用循环
lede: Agent 没有想象中神秘：调用模型，执行工具，把结果交回去，一直循环到模型不再要工具。这个循环三十行就能写完，难的是让它可靠地停下来。
source: 构建有效的 Agent | https://www.anthropic.com/engineering/building-effective-agents ; 为 Agent 编写工具 | https://www.anthropic.com/engineering/writing-tools-for-agents ; OpenAI Python SDK | https://github.com/openai/openai-python ; LangChain4j 工具 | https://docs.langchain4j.dev/tutorials/tools
versions: OpenAI Python SDK 3.42 · Pydantic 2.14 · LangChain4j 1.23
seo_title: AI Agent 开发入门：用 Python 实现智能体工具调用
seo_description: 从零开发一个 AI Agent 智能体：工具调用循环、用装饰器注册工具、最大步数和预算、错误处理、人工确认和流式进度，并和 Java、Kotlin 的 LangChain4j 写法对比。
---

## 什么是 Agent {#what}

Agent 也叫智能体，是在循环里调用模型的程序。模型根据目前的信息决定下一步做什么，程序执行后把结果交回去，直到任务完成。

它和普通程序的区别是，流程由模型决定，不是写死在代码里：

- **工作流**：代码决定步骤，模型只负责其中几步。比如先翻译，再摘要。
- **Agent**：模型决定调用什么工具、调用几次、什么时候结束。

Agent 更灵活，也更贵、更慢、更难预测。步骤能提前确定时，用工作流或者一次模型调用就够了，只有流程确实无法预先写出来时才用 Agent。

## 最小的 Agent {#minimal}

把「Function Calling」一章的两次请求改成循环，就是一个 Agent。模型不再请求工具时，它的回答就是最终结果。

```python
§ import fakellm
§ fakellm.serve(
§     fakellm.tool("get_weather", city="北京"),
§     fakellm.tool("get_clothes", weather="晴"),
§     "今天晴，穿短袖就行",
§ )
§ MODEL = "demo"
import json

from openai import OpenAI

client = OpenAI()

def get_weather(city: str) -> str:
    return "晴"

def get_clothes(weather: str) -> str:
    return "短袖"

TOOLS = {"get_weather": get_weather, "get_clothes": get_clothes}
SCHEMAS = [...]  # 工具定义，写法见 Function Calling 一章
§ SCHEMAS = [{"type": "function", "function": {"name": n, "parameters": {"type": "object"}}} for n in TOOLS]

def run_agent(task: str, max_steps: int = 10) -> str:
    messages = [
        {"role": "system", "content": "你是生活助手，需要时调用工具"},
        {"role": "user", "content": task},
    ]
    for _ in range(max_steps):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return message.content

        for call in message.tool_calls:
            function = TOOLS[call.function.name]
            result = function(**json.loads(call.function.arguments))
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })
    raise RuntimeError("超过最大步数")

print(run_agent("今天北京该穿什么？"))  # => 今天晴，穿短袖就行
```

这段代码已经是完整的 Agent 了。模型先查天气，根据结果再查穿衣建议，最后给出回答，这些步骤都不是代码写死的。

后面的内容都是在这个循环上加东西：更好的工具注册、更可靠的停止条件、错误处理和安全控制。

## 用装饰器注册工具 {#registry}

每个工具都要写一份函数和一份 Schema，很容易不一致。用装饰器把两件事合成一件，函数的类型注解和文档字符串就是工具定义。

Pydantic 的 `TypeAdapter` 能根据函数签名生成 JSON Schema。

:::compare 声明工具
```python
from collections.abc import Callable

from pydantic import TypeAdapter

TOOLS: dict[str, Callable] = {}
SCHEMAS: list[dict] = []

def tool(function: Callable) -> Callable:
    TOOLS[function.__name__] = function
    SCHEMAS.append({
        "type": "function",
        "function": {
            "name": function.__name__,
            "description": function.__doc__,
            "parameters": TypeAdapter(function).json_schema(),
        },
    })
    return function

@tool
def get_weather(city: str, days: int = 1) -> str:
    """查询城市的天气预报"""
    return f"{city} 未来 {days} 天都是晴天"

SCHEMAS[0]["function"]["description"]  # => '查询城市的天气预报'
SCHEMAS[0]["function"]["parameters"]["required"]  # => ['city']
TOOLS["get_weather"]("北京")  # => '北京 未来 1 天都是晴天'
```
```java no-run
class WeatherTools {
    @Tool("查询城市的天气预报")
    String getWeather(@P("城市名") String city, int days) {
        return city + " 未来 " + days + " 天都是晴天";
    }
}
```
```kotlin no-run
class WeatherTools {
    @Tool("查询城市的天气预报")
    fun getWeather(@P("城市名") city: String, days: Int): String =
        "$city 未来 $days 天都是晴天"
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明方式 | 自己写的装饰器 | LangChain4j 的 `@Tool` | LangChain4j 的 `@Tool` |
| 说明 | 文档字符串 | 注解参数 | 注解参数 |
| 收集工具 | 导入模块时注册 | 反射扫描对象 | 反射扫描对象 |
| 参数 Schema | `TypeAdapter` 生成 | 框架生成 | 框架生成 |

> 要点: 装饰器在定义函数时立即运行，模块导入完，工具就注册好了。这和注解不同，注解要靠框架运行时扫描才生效。
:::

## 让框架跑循环 {#framework}

Java 和 Kotlin 一般不自己写循环，LangChain4j 的 `AiServices` 根据接口生成实现，循环、工具调用和记忆都由它负责。Python 里对应的是后面会讲的 LangGraph，以及 OpenAI、Anthropic 各自的 Agent SDK。

学习时建议先手写循环。框架只是替你写了这几十行，出问题时知道里面发生了什么，才查得出来。

:::compare 循环由谁负责
```python
§ import fakellm
§ fakellm.serve(fakellm.tool("get_weather", city="北京"), "北京晴")
§ MODEL = "demo"
§ import json
§ from openai import OpenAI
§ client = OpenAI()
§ TOOLS = {"get_weather": lambda city: "晴"}
§ SCHEMAS = [{"type": "function", "function": {"name": "get_weather", "parameters": {"type": "object"}}}]
def run_agent(task: str, max_steps: int = 10) -> str:
    messages = [{"role": "user", "content": task}]
    for _ in range(max_steps):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            return message.content
        for call in message.tool_calls:
            result = TOOLS[call.function.name](**json.loads(call.function.arguments))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    raise RuntimeError("超过最大步数")

print(run_agent("北京天气？"))  # => 北京晴
```
```java no-run
interface Assistant {
    String chat(String message);
}

void run() {
    var model = OpenAiChatModel.builder()
        .baseUrl(System.getenv("OPENAI_BASE_URL"))
        .apiKey(System.getenv("OPENAI_API_KEY"))
        .modelName("your-model")
        .build();

    var assistant = AiServices.builder(Assistant.class)
        .chatModel(model)
        .tools(new WeatherTools())
        .maxSequentialToolsInvocations(10)
        .build();

    System.out.println(assistant.chat("北京天气？"));
}
§ class WeatherTools {}
```
```kotlin no-run
interface Assistant {
    fun chat(message: String): String
}

fun run() {
    val model = OpenAiChatModel.builder()
        .baseUrl(System.getenv("OPENAI_BASE_URL"))
        .apiKey(System.getenv("OPENAI_API_KEY"))
        .modelName("your-model")
        .build()

    val assistant = AiServices.builder(Assistant::class.java)
        .chatModel(model)
        .tools(WeatherTools())
        .maxSequentialToolsInvocations(10)
        .build()

    println(assistant.chat("北京天气？"))
}
§ class WeatherTools
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 循环 | 自己写 `for` | `AiServices` 生成 | `AiServices` 生成 |
| 限制步数 | `max_steps` | `maxSequentialToolsInvocations` | `maxSequentialToolsInvocations` |
| 中途干预 | 想加什么加什么 | 要用框架提供的扩展点 | 要用框架提供的扩展点 |

> 要点: `AiServices` 的写法和 Retrofit 一样，声明接口，由框架生成实现。
:::

## 让它停下来 {#stop}

循环里最容易出事的是停不下来。模型可能反复调用同一个工具，或者在两个工具之间打转，每一轮都在花钱。至少要有这几道限制：

- **最大步数**：防止无限循环。
- **费用预算**：累计 `usage`，超过预算就停止。
- **总时长**：防止用户一直等待。
- **重复检测**：同样的工具和参数连续出现，说明模型卡住了。

```python
from collections import Counter

class Budget:
    def __init__(self, max_steps: int, max_tokens: int):
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.steps = 0
        self.tokens = 0
        self.calls: Counter[str] = Counter()

    def charge(self, tokens: int) -> None:
        self.steps += 1
        self.tokens += tokens
        if self.steps > self.max_steps:
            raise RuntimeError("超过最大步数")
        if self.tokens > self.max_tokens:
            raise RuntimeError("超过 token 预算")

    def check_repeat(self, name: str, arguments: str, limit: int = 3) -> None:
        self.calls[f"{name}:{arguments}"] += 1
        if self.calls[f"{name}:{arguments}"] > limit:
            raise RuntimeError(f"重复调用 {name}")

budget = Budget(max_steps=5, max_tokens=1000)
budget.charge(400)
budget.charge(400)

try:
    budget.charge(400)
except RuntimeError as e:
    print(e)  # => 超过 token 预算
```

达到上限时，不要直接报错给用户。比较好的做法是再调用一次模型，这次不传工具，让它根据已有信息给出回答，并说明哪些没有完成。

## 处理错误 {#errors}

循环里有三类错误，处理方式不同：

| 错误 | 例子 | 处理方式 |
| --- | --- | --- |
| 工具错误 | 参数不合法、查询没有结果 | 作为结果返回给模型，让它调整 |
| 模型接口错误 | 429、5xx、超时 | SDK 重试，耗尽后中止任务 |
| 程序错误 | 代码有 bug | 记录日志，中止任务 |

把工具错误返回给模型，是 Agent 能自我修复的原因。模型调用了不存在的工具时也一样处理。

```python
import json

TOOLS = {"divide": lambda a, b: a / b}

def execute(name: str, arguments: str) -> str:
    if name not in TOOLS:
        return f"错误：没有 {name} 这个工具，可用的有 {list(TOOLS)}"
    try:
        return str(TOOLS[name](**json.loads(arguments)))
    except json.JSONDecodeError:
        return "错误：参数不是合法的 JSON"
    except (TypeError, ValueError, ZeroDivisionError) as e:
        return f"错误：{e}"

execute("divide", '{"a": 6, "b": 3}')  # => '2.0'
execute("divide", '{"a": 6, "b": 0}')  # => '错误：division by zero'
execute("search", "{}")  # => "错误：没有 search 这个工具，可用的有 ['divide']"
```

## 危险操作要确认 {#approval}

读取类工具可以自动运行。发邮件、付款、删除数据这些操作不能撤销，要等人确认。

模型可能判断错误，也可能被网页里的恶意内容诱导，这在「Prompt Injection」一章会详细讲。确认这一步要写在你的程序里，不能指望提示词。

```python
from collections.abc import Callable

DANGEROUS = {"send_email", "delete_file"}

def execute_with_approval(
    name: str,
    arguments: dict,
    approve: Callable[[str, dict], bool],
) -> str:
    if name in DANGEROUS and not approve(name, arguments):
        return "用户拒绝了这个操作"
    return f"{name} 已执行"

reject = lambda name, arguments: False
accept = lambda name, arguments: True

execute_with_approval("read_file", {}, reject)  # => 'read_file 已执行'
execute_with_approval("send_email", {}, reject)  # => '用户拒绝了这个操作'
execute_with_approval("send_email", {}, accept)  # => 'send_email 已执行'
```

拒绝的结果也是返回给模型，它可以换一种做法，或者向用户说明情况。

## 显示进度 {#events}

Agent 一次任务可能要跑几分钟，用户需要看到它在做什么。把循环改成异步生成器，每一步产出一个事件，再用 SSE 发给前端。

```python
§ import asyncio
§ import fakellm
§ fakellm.serve(fakellm.tool("search", query="Python"), "找到了")
§ MODEL = "demo"
§ from openai import AsyncOpenAI
§ client = AsyncOpenAI()
§ SCHEMAS = [{"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}]
§ async def execute(name, arguments):
§     return "结果"
async def run_agent(task: str):
    messages = [{"role": "user", "content": task}]
    for _ in range(10):
        response = await client.chat.completions.create(
            model=MODEL, messages=messages, tools=SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            yield {"type": "answer", "text": message.content}
            return

        for call in message.tool_calls:
            yield {"type": "tool", "name": call.function.name}
            result = await execute(call.function.name, call.function.arguments)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

§ async def main():
§     print([event async for event in run_agent("搜索")])
§ asyncio.run(main())
```

FastAPI 接口只要 `async for event in run_agent(task): yield ServerSentEvent(data=event)`，写法和「SSE 流式响应」一章完全一样。

:::map Agent 写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| 手写 `for` 循环 | `AiServices` | `AiServices` | Python 里手写也只要几十行 |
| `@tool` 装饰器 | `@Tool` | `@Tool` | 工具定义 |
| `max_steps` | `maxSequentialToolsInvocations` | `maxSequentialToolsInvocations` | 防止无限循环 |
| 异步生成器 | `TokenStream` | `Flow` | 把进度推给前端 |
| `approve` 回调 | `ToolExecutor` 里判断 | `ToolExecutor` 里判断 | 人工确认 |
:::

:::recap
- Agent 是循环：调用模型，执行工具，交回结果，直到模型不再要工具
- 流程能写死时用工作流，确实无法预先确定时才用 Agent
- 用装饰器把函数和工具定义合成一份
- 一定要有最大步数、费用预算和总时长限制
- 工具错误返回给模型，让它自己调整
- 不可撤销的操作由程序要求人工确认，不要依赖提示词
:::
