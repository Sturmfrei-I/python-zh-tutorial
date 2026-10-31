---
id: function-calling
part: 模型能力
title: Function Calling
lede: 模型不能联网，也不能查数据库，但它能说出「我想调用哪个函数」。真正执行的是你的代码，这是所有 Agent 的基础。
source: OpenAI Python SDK | https://github.com/openai/openai-python ; OpenAI Java SDK | https://github.com/openai/openai-java ; DeepSeek 工具调用 | https://api-docs.deepseek.com/zh-cn/guides/tool_calls ; Claude 工具使用 | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md ; 为 Agent 编写工具 | https://www.anthropic.com/engineering/writing-tools-for-agents
versions: OpenAI Python SDK 3.42 · Pydantic 2.14 · OpenAI Java SDK 4.95
seo_title: Function Calling 教程：大模型工具调用完整流程
seo_description: 讲清大模型开发必学的 Function Calling：定义工具、解析 tool_calls、执行函数并回传结果、并行调用、tool_choice、错误处理和工具设计，附 Python、Java、Kotlin 代码。
---

## 工作流程 {#flow}

模型本身只会生成文字。Function Calling 让它能输出一段结构化的「调用请求」，由你的程序执行，再把结果交回去。

整个过程是两次请求：

1. 你发送消息和工具列表。
2. 模型回复：要调用 `get_weather`，参数是 `{"city": "北京"}`。这时 `finish_reason` 是 `tool_calls`。
3. 你的代码执行函数，得到结果。
4. 你把结果作为 `tool` 消息加进历史，再发一次请求。
5. 模型根据结果写出最终回答。

模型不会执行任何东西，它只决定调用什么。这对安全很重要：能做什么，完全由你提供的工具决定。

## 定义工具 {#define}

工具用 JSON Schema 描述：名字、用途和参数。这些内容会发给模型，并占用 token。

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询城市当前的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名，比如北京"},
            },
            "required": ["city"],
        },
    },
}]
```

手写 Schema 容易和代码不一致。用 Pydantic 生成更稳妥，类的文档字符串和 `Field` 的说明都会保留，详见「Pydantic 数据校验」。

:::compare 用类型定义工具
```python
import openai
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    """查询城市当前的天气"""
    city: str = Field(description="城市名，比如北京")

tool = openai.pydantic_function_tool(GetWeather, name="get_weather")

tool["function"]["name"]  # => 'get_weather'
tool["function"]["description"]  # => '查询城市当前的天气'
tool["function"]["parameters"]["required"]  # => ['city']
```
```java no-run
@JsonClassDescription("查询城市当前的天气")
static class GetWeather {
    @JsonPropertyDescription("城市名，比如北京")
    public String city;
}

void run() {
    var params = ChatCompletionCreateParams.builder()
        .model("your-model")
        .addUserMessage("北京今天天气怎么样？")
        .addTool(GetWeather.class)
        .build();
}
```
```kotlin no-run
§ import com.fasterxml.jackson.annotation.JsonClassDescription
§ import com.fasterxml.jackson.annotation.JsonPropertyDescription
@JsonClassDescription("查询城市当前的天气")
class GetWeather {
    @JsonPropertyDescription("城市名，比如北京")
    var city: String = ""
}

fun run() {
    val params = ChatCompletionCreateParams.builder()
        .model("your-model")
        .addUserMessage("北京今天天气怎么样？")
        .addTool(GetWeather::class.java)
        .build()
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明参数 | Pydantic 模型 | 普通类 | 普通类 |
| 用途说明 | 文档字符串 | `@JsonClassDescription` | `@JsonClassDescription` |
| 字段说明 | `Field(description=...)` | `@JsonPropertyDescription` | `@JsonPropertyDescription` |

> 要点: `pydantic_function_tool` 生成的是严格模式，会带上 `strict: true`。有些兼容服务不接受这个字段，那就用 `model_json_schema()` 自己组装。
:::

## 完整的一次调用 {#call}

把流程写成代码。第一次响应的 `message.tool_calls` 列出要调用的函数，`arguments` 是 JSON 字符串，要自己解析。

:::compare 调用工具并返回结果
```python
§ import fakellm
§ fakellm.serve(fakellm.tool("get_weather", city="北京"), "北京今天晴，25 度")
§ MODEL = "demo"
import json

import openai
from openai import OpenAI
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    """查询城市当前的天气"""
    city: str = Field(description="城市名")

def get_weather(city: str) -> str:
    return json.dumps({"city": city, "weather": "晴", "temperature": 25})

client = OpenAI()
tools = [openai.pydantic_function_tool(GetWeather, name="get_weather")]
messages = [{"role": "user", "content": "北京今天天气怎么样？"}]

response = client.chat.completions.create(
    model=MODEL, messages=messages, tools=tools,
)
message = response.choices[0].message
messages.append(message.model_dump(exclude_none=True))

for call in message.tool_calls:
    arguments = GetWeather.model_validate_json(call.function.arguments)
    messages.append({
        "role": "tool",
        "tool_call_id": call.id,
        "content": get_weather(arguments.city),
    })

final = client.chat.completions.create(
    model=MODEL, messages=messages, tools=tools,
)
print(final.choices[0].message.content)  # => 北京今天晴，25 度
```
```java no-run
@JsonClassDescription("查询城市当前的天气")
static class GetWeather {
    @JsonPropertyDescription("城市名")
    public String city;

    String execute() {
        return "{\"weather\": \"晴\", \"temperature\": 25}";
    }
}

void run(OpenAIClient client) {
    var builder = ChatCompletionCreateParams.builder()
        .model("your-model")
        .addUserMessage("北京今天天气怎么样？")
        .addTool(GetWeather.class);

    var message = client.chat().completions().create(builder.build())
        .choices().get(0).message();
    builder.addMessage(message);

    for (var call : message.toolCalls().orElse(List.of())) {
        var function = call.asFunction();
        var arguments = function.function().arguments(GetWeather.class);
        builder.addMessage(ChatCompletionToolMessageParam.builder()
            .toolCallId(function.id())
            .contentAsJson(arguments.execute())
            .build());
    }

    var answer = client.chat().completions().create(builder.build());
    System.out.println(
        answer.choices().get(0).message().content().orElse(""));
}
```
```kotlin no-run
§ import com.fasterxml.jackson.annotation.JsonClassDescription
§ import com.fasterxml.jackson.annotation.JsonPropertyDescription
@JsonClassDescription("查询城市当前的天气")
class GetWeather {
    @JsonPropertyDescription("城市名")
    var city: String = ""

    fun execute() = """{"weather": "晴", "temperature": 25}"""
}

fun run(client: OpenAIClient) {
    val builder = ChatCompletionCreateParams.builder()
        .model("your-model")
        .addUserMessage("北京今天天气怎么样？")
        .addTool(GetWeather::class.java)

    val message = client.chat().completions().create(builder.build())
        .choices()[0].message()
    builder.addMessage(message)

    for (call in message.toolCalls().orElse(emptyList())) {
        val function = call.asFunction()
        val arguments = function.function()
            .arguments(GetWeather::class.java)
        builder.addMessage(
            ChatCompletionToolMessageParam.builder()
                .toolCallId(function.id())
                .contentAsJson(arguments.execute())
                .build(),
        )
    }

    val answer = client.chat().completions().create(builder.build())
    println(answer.choices()[0].message().content().orElse(""))
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 取工具调用 | `message.tool_calls` | `message.toolCalls()` | `message.toolCalls()` |
| 解析参数 | `model_validate_json` | `arguments(类)` | `arguments(类)` |
| 回传结果 | 追加 `role="tool"` 的字典 | `ChatCompletionToolMessageParam` | `ChatCompletionToolMessageParam` |
| 对应关系 | `tool_call_id` | `toolCallId` | `toolCallId` |

> 要点: `assistant` 那条带 `tool_calls` 的消息必须先放进历史，后面的 `tool` 消息用 `tool_call_id` 和它对应。缺了任何一步，接口都会返回 400。
:::

## 并行调用 {#parallel}

模型一次可能要求调用多个工具，比如同时查两个城市。`tool_calls` 是列表，每一项都要执行，并且都要回传，结果的顺序不重要，靠 `tool_call_id` 对应。

```python
§ import fakellm
§ fakellm.serve(fakellm.tools(("get_weather", {"city": "北京"}), ("get_weather", {"city": "上海"})))
§ MODEL = "demo"
import json
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

def get_weather(city: str) -> str:
    return f"{city}：晴"

client = OpenAI()
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "北京和上海的天气？"}],
)

def run(call) -> dict:
    arguments = json.loads(call.function.arguments)
    return {
        "role": "tool",
        "tool_call_id": call.id,
        "content": get_weather(**arguments),
    }

with ThreadPoolExecutor() as pool:
    results = list(pool.map(run, response.choices[0].message.tool_calls))

[r["content"] for r in results]  # => ['北京：晴', '上海：晴']
```

工具之间有先后依赖时，用 `parallel_tool_calls=False` 让模型每次只调用一个。

## 控制是否调用 {#choice}

`tool_choice` 决定模型能不能调用工具：

| 值 | 含义 |
| --- | --- |
| `"auto"` | 默认值，模型自己决定 |
| `"none"` | 不调用工具，直接回答 |
| `"required"` | 必须调用某个工具 |
| 指定函数名 | 必须调用这个工具 |

不是所有模型都支持后两种。比如 Claude 的最新模型不再接受强制调用，要改用 `auto`，再在提示词里写清楚。

## 处理工具错误 {#errors}

工具出错时不要抛异常中断流程，把错误信息作为结果返回。模型读到错误后往往能自己修正，比如换一个参数重试。

```python
import json

from pydantic import BaseModel, Field, ValidationError

class GetWeather(BaseModel):
    city: str = Field(min_length=1)

def execute(arguments: str) -> str:
    try:
        parsed = GetWeather.model_validate_json(arguments)
    except ValidationError as e:
        return json.dumps({"error": "参数不对", "detail": e.errors(include_url=False)[0]["msg"]}, ensure_ascii=False)
    if parsed.city == "火星":
        return json.dumps({"error": "不支持这个城市"}, ensure_ascii=False)
    return json.dumps({"weather": "晴"}, ensure_ascii=False)

print(execute('{"city": "北京"}'))  # => {"weather": "晴"}
print(execute('{"city": "火星"}'))  # => {"error": "不支持这个城市"}
print(execute('{"city": ""}'))  # => {"error": "参数不对", "detail": "String should have at least 1 character"}
```

模型生成的参数可能不合法，甚至不是合法的 JSON，所以一定要校验。严格模式能减少这类问题，但不是所有服务都支持。

## 把工具写好 {#design}

工具的说明是写给模型看的文档，直接决定它会不会用对：

- **名字和说明要明确。** `search_orders` 比 `search` 好。说明里写清楚什么时候该用，什么时候不该用。
- **参数要少而具体。** 用枚举代替自由文本，给出取值示例。
- **返回精简的结果。** 工具结果会进入上下文。返回 10 万字的日志，既费钱又干扰模型，要先筛选和分页。
- **错误要说明怎么改。** 「日期格式应为 YYYY-MM-DD」比「参数错误」有用得多。
- **工具不要太多。** 工具越多，模型越容易选错，定义本身也占 token。功能相近的合并成一个。

:::more 流式响应里的工具调用
`stream=True` 时，工具调用也是分片到达的：第一个片段带 `id` 和函数名，后面的片段只带 `arguments` 的一小段。要按 `index` 把每个调用的 `arguments` 拼起来，等 `finish_reason` 出现后再解析。

这也是为什么要等拼完才能 `json.loads`，中途的内容不是合法 JSON。
:::

:::map Function Calling 写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `pydantic_function_tool(Model)` | `.addTool(类)` | `.addTool(类)` | 用类型生成 Schema |
| `Field(description=...)` | `@JsonPropertyDescription` | `@JsonPropertyDescription` | 说明会发给模型 |
| `message.tool_calls` | `message.toolCalls()` | `message.toolCalls()` | 模型要调用的函数 |
| `role="tool"` | `ChatCompletionToolMessageParam` | `ChatCompletionToolMessageParam` | 回传结果 |
| `tool_choice="none"` | `.toolChoice(...)` | `.toolChoice(...)` | 控制是否调用 |
:::

:::recap
- 模型只决定调用什么，真正执行的是你的代码
- 工具用 JSON Schema 描述，用 Pydantic 生成更可靠
- 流程是两次请求：拿到 `tool_calls`，执行后追加 `tool` 消息再请求一次
- `assistant` 消息和 `tool` 消息用 `tool_call_id` 对应，缺一不可
- 参数一定要校验，工具出错时把错误作为结果返回给模型
- 说明写清楚，结果要精简，工具数量要克制
:::
