---
id: structured-output
part: 模型能力
title: 结构化输出
lede: 程序要的是字段，不是一段话。让模型按 JSON Schema 输出，再用 Pydantic 校验，大模型的回答就能接进普通的业务代码。
source: OpenAI 结构化输出 | https://developers.openai.com/api/docs/guides/structured-outputs ; OpenAI Python SDK | https://github.com/openai/openai-python ; DeepSeek JSON Output | https://api-docs.deepseek.com/zh-cn/guides/json_mode ; Claude 结构化输出 | https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md ; Pydantic JSON Schema | https://docs.pydantic.dev/latest/concepts/json_schema/
versions: OpenAI Python SDK 3.42 · Pydantic 2.14 · OpenAI Java SDK 4.95
seo_title: 大模型结构化输出教程：JSON Schema 和 Pydantic
seo_description: 让大模型输出可靠的 JSON：JSON mode 和 Structured Outputs 的区别、用 Pydantic 解析、严格模式的要求、校验失败后重试，并和 Java、Kotlin 的写法对比。
---

## 三种做法 {#levels}

要从模型拿到结构化数据，有三种做法，可靠程度依次提高：

| 做法 | 能保证什么 | 怎么用 |
| --- | --- | --- |
| 在提示词里要求 JSON | 什么也不保证 | 自己解析，可能混入说明文字 |
| JSON mode | 输出是合法的 JSON，字段不保证 | `response_format={"type": "json_object"}` |
| Structured Outputs | 输出符合你给的 Schema | `response_format` 传 `json_schema` |

优先用 Structured Outputs。服务商不支持时退回 JSON mode，再加上校验和重试。

## 用 Pydantic 解析 {#parse}

SDK 的 `parse` 方法接收 Pydantic 模型，自动把它转成 Schema 发给模型，再把回答解析成对象。

:::compare 解析成对象
```python
§ import fakellm
§ fakellm.serve('{"name": "Ada", "age": 36, "skills": ["Python", "Kotlin"]}')
§ MODEL = "demo"
from openai import OpenAI
from pydantic import BaseModel

class Resume(BaseModel):
    name: str
    age: int
    skills: list[str]

client = OpenAI()
response = client.chat.completions.parse(
    model=MODEL,
    messages=[
        {"role": "system", "content": "从文本里提取简历信息"},
        {"role": "user", "content": "Ada，36 岁，会 Python 和 Kotlin"},
    ],
    response_format=Resume,
)

resume = response.choices[0].message.parsed
print(resume.name)  # => Ada
print(resume.skills)  # => ['Python', 'Kotlin']
```
```java no-run
record Resume(String name, int age, List<String> skills) {}

void run(OpenAIClient client) {
    var params = StructuredChatCompletionCreateParams.<Resume>builder()
        .model("your-model")
        .addSystemMessage("从文本里提取简历信息")
        .addUserMessage("Ada，36 岁，会 Python 和 Kotlin")
        .responseFormat(Resume.class)
        .build();

    var response = client.chat().completions().create(params);
    response.choices().get(0).message().content()
        .ifPresent(resume -> System.out.println(resume.name()));
}
```
```kotlin no-run
data class Resume(
    val name: String = "",
    val age: Int = 0,
    val skills: List<String> = emptyList(),
)

fun run(client: OpenAIClient) {
    val params = com.openai.models.chat.completions
        .StructuredChatCompletionCreateParams.builder<Resume>()
        .model("your-model")
        .addSystemMessage("从文本里提取简历信息")
        .addUserMessage("Ada，36 岁，会 Python 和 Kotlin")
        .responseFormat(Resume::class.java)
        .build()

    val response = client.chat().completions().create(params)
    response.choices()[0].message().content()
        .ifPresent { println(it.name) }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明结构 | Pydantic 模型 | `record` | `data class` |
| 指定结构 | `response_format=模型` | `.responseFormat(类)` | `.responseFormat(类)` |
| 取结果 | `message.parsed` | `message().content()` | `message().content()` |

> 要点: Schema 也要占 token，字段的 `description` 就是写给模型的提示，复杂字段要写清楚。
:::

看一下 SDK 实际发出去的内容，它把模型转成了严格模式的 Schema：

```python
§ import json
§ import fakellm
§ fakellm.serve('{"name": "Ada"}')
§ MODEL = "demo"
from openai import OpenAI
from pydantic import BaseModel

class Person(BaseModel):
    name: str

client = OpenAI()
client.chat.completions.parse(model=MODEL, messages=[], response_format=Person)

sent = fakellm.requests[0]["response_format"]
sent["type"]  # => 'json_schema'
sent["json_schema"]["strict"]  # => True
sent["json_schema"]["schema"]["additionalProperties"]  # => False
```

## 严格模式的限制 {#strict}

严格模式能保证输出符合 Schema，代价是 Schema 的写法受限：

- 所有字段都要出现在 `required` 里，`additionalProperties` 必须是 `false`。SDK 会替你处理。
- 可选字段写成 `str | None`，让模型明确填 `null`。
- 第一次使用某个 Schema 时，服务端要先处理它，这次请求可能会慢一些。

取值有限时用 `Literal` 或枚举，模型就不会输出范围以外的值。这比在提示词里要求可靠。

```python
from typing import Literal

from pydantic import BaseModel, Field

class Ticket(BaseModel):
    category: Literal["账单", "技术", "其他"]
    urgent: bool
    summary: str = Field(description="一句话概括问题")
    order_id: str | None = Field(description="订单号，没有时填 null")

Ticket.model_json_schema()["properties"]["category"]  # => {'enum': ['账单', '技术', '其他'], 'title': 'Category', 'type': 'string'}
```

分类、抽取和路由这类任务用这个写法最合适，比如把用户请求分到不同的处理流程。

## 模型也会失败 {#failure}

Schema 能约束格式，约束不了所有情况。使用结果之前要处理这几种情况：

- **拒绝回答**：`message.refusal` 不为空，这时 `parsed` 是 `None`。
- **输出被截断**：达到 `max_tokens` 时 JSON 不完整。`parse` 会抛 `LengthFinishReasonError`。
- **内容不对**：格式正确，但数据是编的。Schema 查不出这种错误，这要靠评测。

```python
§ import fakellm
§ fakellm.serve({"role": "assistant", "content": None, "refusal": "无法处理这个请求"})
§ MODEL = "demo"
from openai import OpenAI
from pydantic import BaseModel

class Result(BaseModel):
    value: str

client = OpenAI()
response = client.chat.completions.parse(
    model=MODEL,
    messages=[{"role": "user", "content": "..."}],
    response_format=Result,
)

message = response.choices[0].message
if message.refusal:
    print("模型拒绝了：", message.refusal)  # => 模型拒绝了： 无法处理这个请求
else:
    print(message.parsed.value)
```

## 校验失败时重试 {#retry}

有些规则 Schema 表达不了，比如结束日期要晚于开始日期。服务商只支持 JSON mode 时，字段也可能不对。

这时用 Pydantic 校验，失败就把错误发回给模型，让它改正。这个循环很小，效果却很好。

:::compare 带校验的重试
```python
§ import fakellm
§ fakellm.serve('{"start": 5, "end": 1}', '{"start": 1, "end": 5}')
§ MODEL = "demo"
import json

from openai import OpenAI
from pydantic import BaseModel, ValidationError, model_validator

class Period(BaseModel):
    start: int
    end: int

    @model_validator(mode="after")
    def check(self):
        if self.end <= self.start:
            raise ValueError("end 要大于 start")
        return self

client = OpenAI()

def extract(text: str, attempts: int = 3) -> Period:
    messages = [
        {"role": "system", "content": "输出 JSON，字段是 start 和 end"},
        {"role": "user", "content": text},
    ]
    for _ in range(attempts):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        try:
            return Period.model_validate_json(content)
        except ValidationError as e:
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": f"输出有误，请修正：{e}"})
    raise RuntimeError("多次重试后仍然失败")

print(extract("从 1 号到 5 号"))  # => start=1 end=5
```
```java no-run
record Period(int start, int end) {
    Period {
        if (end <= start) {
            throw new IllegalArgumentException("end 要大于 start");
        }
    }
}

Period extract(Function<String, String> callModel, String text) {
    var prompt = text;
    for (var i = 0; i < 3; i++) {
        var content = callModel.apply(prompt);
        try {
            return mapper.readValue(content, Period.class);
        } catch (Exception e) {
            prompt = text + "\n上次输出有误，请修正：" + e.getMessage();
        }
    }
    throw new IllegalStateException("多次重试后仍然失败");
}
§ ObjectMapper mapper;
```
```kotlin no-run
@Serializable
data class Period(val start: Int, val end: Int) {
    init {
        require(end > start) { "end 要大于 start" }
    }
}

fun extract(callModel: (String) -> String, text: String): Period {
    var prompt = text
    repeat(3) {
        val content = callModel(prompt)
        try {
            return Json.decodeFromString<Period>(content)
        } catch (e: IllegalArgumentException) {
            prompt = "$text\n上次输出有误，请修正：${e.message}"
        }
    }
    error("多次重试后仍然失败")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 业务校验 | `model_validator` | 紧凑构造函数 | `init` 里的 `require` |
| 失败时 | `ValidationError` 带字段信息 | 异常信息 | 异常信息 |
| 重试 | 把错误追加进消息 | 把错误拼进提示词 | 把错误拼进提示词 |

> 要点: 重试次数要有上限，每次重试都要花钱。多次失败通常说明提示词或 Schema 有问题，要改的是它们。
:::

:::warn JSON mode 的坑
部分服务要求提示词里出现 `json` 这个词，否则会报错。DeepSeek 的文档还提到，模型输出不了 JSON 时 `content` 可能只有空白，这时 `finish_reason` 仍然是 `stop`。代码里要处理空内容。
:::

:::map 结构化输出写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `chat.completions.parse()` | `create(structuredParams)` | `create(structuredParams)` | 自动解析 |
| `response_format=Model` | `.responseFormat(类)` | `.responseFormat(类)` | 用类型生成 Schema |
| `Literal["a", "b"]` | `enum` | `enum class` | 限制取值 |
| `str \| None` | `Optional<String>` | `String?` | 严格模式的可选字段 |
| `message.refusal` | `message().refusal()` | `message().refusal()` | 模型拒绝回答 |
:::

:::recap
- 优先用 Structured Outputs，不支持时用 JSON mode 加校验
- `parse` 接收 Pydantic 模型，结果在 `message.parsed`
- 严格模式下所有字段都必填，可选字段写成 `str | None`
- 取值有限时用 `Literal`，比在提示词里要求可靠
- 使用前检查 `refusal` 和截断，业务规则用校验器，失败时带错误重试
- Schema 只约束格式，内容对不对要靠评测
:::
