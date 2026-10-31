---
id: llm-api
part: 调用模型
title: 调用大模型接口
lede: 大模型开发从调用接口开始：发一组消息，收一段回答。这一章从第一次调用讲起，再处理多轮对话、流式输出和错误。
source: OpenAI Python SDK | https://github.com/openai/openai-python ; OpenAI Java SDK | https://github.com/openai/openai-java ; OpenAI API 参考 | https://developers.openai.com/api/reference/python/ ; DeepSeek 快速开始 | https://api-docs.deepseek.com/zh-cn/ ; Claude Messages API | https://platform.claude.com/docs/en/api/messages
versions: OpenAI Python SDK 3.42 · OpenAI Java SDK 4.95
seo_title: 大模型开发入门：OpenAI 兼容 API 调用和流式输出
seo_description: 大模型开发入门：用 Python 调用大模型 API，讲解消息格式、OpenAI 兼容接口、多轮对话、流式输出、finish_reason、错误和重试，并和 Java、Kotlin 的 SDK 写法对比。
---

## 接口长什么样 {#shape}

大模型接口是普通的 HTTP POST。请求里是一组消息，响应里是模型生成的下一条消息。每条消息有一个角色：

- `system`：给模型的指令，规定身份、规则和输出格式
- `user`：用户说的话
- `assistant`：模型之前的回答
- `tool`：工具调用的结果，后面的章节会讲

下面是一次请求和响应的主要内容。服务端不保存对话，所以这就是一次调用的全部信息。

```json
{
  "model": "your-model",
  "messages": [
    {"role": "system", "content": "你是翻译助手，只输出译文"},
    {"role": "user", "content": "Hello, world"}
  ]
}
```

```json
{
  "choices": [{
    "message": {"role": "assistant", "content": "你好，世界"},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 23, "completion_tokens": 5, "total_tokens": 28}
}
```

这个格式最早由 OpenAI 定义，DeepSeek、通义千问、Kimi 等服务都提供了兼容的接口，所以大家把它叫做 OpenAI 兼容接口。本站的大模型章节都按这个格式写。

## 第一次调用 {#first}

用官方 SDK 比自己发 HTTP 请求省事，它处理了序列化、重试和流式解析。

```bash
pip install openai
```

先设置环境变量。`OPENAI_BASE_URL` 决定请求发到哪里，换服务商时一般只改这一项和 Key。

```bash
export OPENAI_API_KEY="你的 Key"
export OPENAI_BASE_URL="https://api.deepseek.com"
```

示例里的 `MODEL` 换成服务商提供的模型名。模型更新很快，本站不写死具体名字。

:::compare 发送一次请求
```python
§ import fakellm
§ fakellm.serve("你好，世界")
from openai import OpenAI

MODEL = "your-model"
client = OpenAI()  # 从环境变量读取地址和 Key

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "你是翻译助手，只输出译文"},
        {"role": "user", "content": "Hello, world"},
    ],
)

print(response.choices[0].message.content)  # => 你好，世界
```
```java no-run
§ void run() {
OpenAIClient client = OpenAIOkHttpClient.fromEnv();

var params = ChatCompletionCreateParams.builder()
    .model(MODEL)
    .addSystemMessage("你是翻译助手，只输出译文")
    .addUserMessage("Hello, world")
    .build();

var response = client.chat().completions().create(params);
System.out.println(
    response.choices().get(0).message().content().orElse(""));
§ }
§ static final String MODEL = "your-model";
```
```kotlin no-run
§ const val MODEL = "your-model"
§ fun run() {
val client = OpenAIOkHttpClient.fromEnv()

val params = ChatCompletionCreateParams.builder()
    .model(MODEL)
    .addSystemMessage("你是翻译助手，只输出译文")
    .addUserMessage("Hello, world")
    .build()

val response = client.chat().completions().create(params)
println(response.choices()[0].message().content().orElse(""))
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 客户端 | `OpenAI()` | `OpenAIOkHttpClient.fromEnv()` | `OpenAIOkHttpClient.fromEnv()` |
| 请求参数 | 关键字参数，消息是字典 | Builder | Builder |
| 回答内容 | 字符串或 `None` | `Optional<String>` | `Optional<String>` |
| 线程 | 同步阻塞，有 `AsyncOpenAI` | 同步阻塞，有 `async()` | 同步阻塞，有 `async()` |

> 要点: Java 和 Kotlin 共用一个 SDK，底层是 OkHttp。`messages` 在 Python 里就是字典列表，和 JSON 一一对应。
:::

`client` 和数据库的 `engine` 一样，只创建一个，全局共用。在 FastAPI 的 `async def` 接口里要用 `AsyncOpenAI`，用法相同，调用时加 `await`。

## 换一家服务商 {#providers}

兼容接口的好处是换服务商几乎不改代码。也可以不用环境变量，在创建客户端时指定：

```python
§ import os
§ os.environ.pop("OPENAI_API_KEY", None)
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="你的 Key",
)
client.base_url.host  # => 'api.deepseek.com'
```

「兼容」不等于完全相同。常见的差异有这些，换服务商时要逐项确认：

- 结构化输出：有的只支持 `json_object`，不支持 `json_schema`
- 提示缓存：开启方式和 `usage` 里的字段都不一样
- 参数：有的模型不接受 `temperature`，有的返回额外字段，比如思考内容

Claude 有自己的 Messages API，消息格式略有不同，比如 `system` 是单独的顶层参数，并且必须传 `max_tokens`。需要用到它的专有功能时，直接用 Anthropic 的 SDK。

## 多轮对话 {#history}

接口没有状态，模型记不住上一次请求。所谓记忆，是客户端把历史消息全部重新发一遍。

:::compare 多轮对话
```python
§ import fakellm
§ fakellm.serve("你好，Ada", "你叫 Ada")
§ MODEL = "demo"
from openai import OpenAI

client = OpenAI()
messages = [{"role": "system", "content": "你是聊天助手"}]

def chat(text: str) -> str:
    messages.append({"role": "user", "content": text})
    response = client.chat.completions.create(model=MODEL, messages=messages)
    answer = response.choices[0].message.content
    messages.append({"role": "assistant", "content": answer})
    return answer

print(chat("我叫 Ada"))  # => 你好，Ada
print(chat("我叫什么？"))  # => 你叫 Ada
len(messages)  # => 5
```
```java no-run
§ static final String MODEL = "your-model";
String chat(OpenAIClient client, List<ChatCompletionMessageParam> history,
        String text) {
    history.add(ChatCompletionMessageParam.ofUser(
        ChatCompletionUserMessageParam.builder().content(text).build()));

    var params = ChatCompletionCreateParams.builder()
        .model(MODEL)
        .messages(history)
        .build();
    var message = client.chat().completions().create(params)
        .choices().get(0).message();

    history.add(ChatCompletionMessageParam.ofAssistant(message.toParam()));
    return message.content().orElse("");
}
```
```kotlin no-run
§ const val MODEL = "your-model"
fun chat(
    client: OpenAIClient,
    history: MutableList<ChatCompletionMessageParam>,
    text: String,
): String {
    history += ChatCompletionMessageParam.ofUser(
        ChatCompletionUserMessageParam.builder().content(text).build(),
    )

    val params = ChatCompletionCreateParams.builder()
        .model(MODEL)
        .messages(history)
        .build()
    val message = client.chat().completions().create(params)
        .choices()[0].message()

    history += ChatCompletionMessageParam.ofAssistant(message.toParam())
    return message.content().orElse("")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 历史记录 | 字典列表 | `List<ChatCompletionMessageParam>` | `MutableList` |
| 保存回答 | 自己拼一个字典 | `message.toParam()` | `message.toParam()` |

> 要点: 每一轮都要发送完整历史，所以对话越长，每次请求的 token 越多，费用也越高。下一章讲怎么控制。
:::

## 流式输出 {#stream}

加上 `stream=True`，SDK 返回一个迭代器，内容一段一段到达。每个片段放在 `delta` 里，不是 `message`。

流式请求默认不返回用量。要统计 token 时加上 `stream_options={"include_usage": True}`，最后一个片段会带 `usage`，它的 `choices` 是空列表。

:::compare 流式读取回答
```python
§ import fakellm
§ fakellm.serve("你好")
§ MODEL = "demo"
from openai import OpenAI

client = OpenAI()
stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "打个招呼"}],
    stream=True,
    stream_options={"include_usage": True},
)

answer = ""
for chunk in stream:
    if chunk.usage:
        print(chunk.usage.total_tokens)  # => 17
    elif chunk.choices[0].delta.content:
        answer += chunk.choices[0].delta.content

print(answer)  # => 你好
```
```java no-run
§ void run(OpenAIClient client, ChatCompletionCreateParams params) {
try (var stream = client.chat().completions().createStreaming(params)) {
    stream.stream()
        .flatMap(chunk -> chunk.choices().stream())
        .flatMap(choice -> choice.delta().content().stream())
        .forEach(System.out::print);
}
§ }
```
```kotlin no-run
fun answer(
    client: OpenAIClient,
    params: ChatCompletionCreateParams,
): Flow<String> = flow {
    client.chat().completions().createStreaming(params).use { stream ->
        for (chunk in stream.stream()) {
            val text = chunk.choices().firstOrNull()?.delta()?.content()
            text?.orElse(null)?.let { emit(it) }
        }
    }
}.flowOn(Dispatchers.IO)
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 开启 | `stream=True` | `createStreaming` | `createStreaming` |
| 读取 | `for` 循环 | `Stream` | 包成 `Flow` |
| 关闭 | 读完自动关闭 | `try` 自动关闭 | `use` 自动关闭 |
| 增量内容 | `delta.content` | `delta().content()` | `delta().content()` |

> 要点: 片段的 `content` 可能是 `None`，第一个和最后一个片段常常没有文字，要先判断。
:::

在 FastAPI 里，用 `AsyncOpenAI` 配合「SSE 流式响应」一章的异步生成器，就能把回答实时转发给前端。

```python
§ import asyncio
§ import fakellm
§ fakellm.serve("你好")
§ MODEL = "demo"
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def call_model(prompt: str):
    stream = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

§ async def main():
§     print("".join([piece async for piece in call_model("hi")]))  # => 你好
§ asyncio.run(main())
```

## 检查结束原因 {#finish}

`finish_reason` 说明模型为什么停下来。不检查它，回答被截断时你不会知道。

| 值 | 含义 | 该怎么办 |
| --- | --- | --- |
| `stop` | 正常结束 | 直接使用 |
| `length` | 达到 `max_tokens` 或上下文上限 | 内容不完整，调大上限或缩短输入 |
| `tool_calls` | 模型要调用工具 | 执行工具后继续，见「Function Calling」 |
| `content_filter` | 被安全策略拦截 | 提示用户，不要直接重试 |

## 错误和重试 {#errors}

SDK 默认重试 2 次，连接错误、408、409、429 和 5xx 都会自动重试。默认超时是 10 分钟，交互式应用要调短。

异常按状态码分类，常见的有下面这些。重试耗尽后才会抛出来。

:::compare 处理错误
```python
§ import fakellm
§ fakellm.serve(fakellm.error(429, "请求太频繁"))
§ MODEL = "demo"
import openai
from openai import OpenAI

client = OpenAI(timeout=60, max_retries=0)

def ask(text: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": text}],
        )
    except openai.RateLimitError:
        return "请求太多，请稍后再试"
    except openai.APITimeoutError:
        return "模型响应超时"
    except openai.APIStatusError as e:
        return f"接口错误 {e.status_code}"
    return response.choices[0].message.content

print(ask("你好"))  # => 请求太多，请稍后再试
```
```java no-run
§ static final ChatCompletionCreateParams PARAMS = null;
String ask() {
    var client = OpenAIOkHttpClient.builder()
        .fromEnv()
        .timeout(Duration.ofSeconds(60))
        .maxRetries(0)
        .build();
    try {
        var response = client.chat().completions().create(PARAMS);
        return response.choices().get(0).message().content().orElse("");
    } catch (RateLimitException e) {
        return "请求太多，请稍后再试";
    } catch (OpenAIServiceException e) {
        return "接口错误 " + e.statusCode();
    }
}
```
```kotlin no-run
fun ask(params: ChatCompletionCreateParams): String {
    val client = OpenAIOkHttpClient.builder()
        .fromEnv()
        .timeout(java.time.Duration.ofSeconds(60))
        .maxRetries(0)
        .build()
    return try {
        client.chat().completions().create(params)
            .choices()[0].message().content().orElse("")
    } catch (e: RateLimitException) {
        "请求太多，请稍后再试"
    } catch (e: OpenAIServiceException) {
        "接口错误 ${e.statusCode()}"
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 限流 | `RateLimitError` | `RateLimitException` | `RateLimitException` |
| 其他状态码 | `APIStatusError` | `OpenAIServiceException` | `OpenAIServiceException` |
| 配置重试 | `max_retries` | `maxRetries` | `maxRetries` |
| 配置超时 | `timeout` | `timeout` | `timeout` |

> 要点: `except` 从具体到宽泛排列，`RateLimitError` 是 `APIStatusError` 的子类。400 这类错误重试也不会成功。
:::

## 保管好 Key {#key}

API Key 就是钱。`.env` 放进 `.gitignore`，线上用环境变量注入。

:::warn 不要把 Key 打进 App
APK 里的字符串很容易被提取出来。Android 应用不能直接调用大模型接口，要由自己的服务端转发。服务端负责鉴权、限流和记录用量，这也是前面 FastAPI 和 SSE 章节要解决的问题。
:::

:::map 大模型 SDK 写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `OpenAI()` | `OpenAIOkHttpClient.fromEnv()` | `OpenAIOkHttpClient.fromEnv()` | 全局一个 |
| `AsyncOpenAI()` | `client.async()` | `client.async()` | 协程里用它 |
| `messages=[{...}]` | `.addUserMessage()` | `.addUserMessage()` | 消息列表 |
| `stream=True` | `createStreaming()` | `createStreaming()` | 流式输出 |
| `chunk.choices[0].delta` | `choice.delta()` | `choice.delta()` | 增量内容 |
| `RateLimitError` | `RateLimitException` | `RateLimitException` | 429 |
:::

:::recap
- 大模型接口是 HTTP POST：发消息列表，收下一条消息，服务端不保存状态
- 兼容接口换服务商主要改 `base_url` 和 Key，但高级功能各家有差异
- 多轮对话靠每次重新发送全部历史
- 流式用 `stream=True`，内容在 `delta` 里，用量要单独打开
- 检查 `finish_reason`，`length` 表示回答被截断
- SDK 自带重试，交互式应用要调短超时，Key 只放在服务端
:::
