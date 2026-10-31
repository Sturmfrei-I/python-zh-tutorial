---
id: tokens
part: 调用模型
title: token 和上下文窗口
lede: 大模型按 token 计费，也按 token 限制输入长度。搞清楚 token 怎么算，就知道费用从哪来，也知道对话变长时该怎么办。
source: tiktoken | https://github.com/openai/tiktoken ; DeepSeek 模型与价格 | https://api-docs.deepseek.com/zh-cn/quick_start/pricing ; Claude 令牌计数 | https://platform.claude.com/docs/en/build-with-claude/token-counting.md ; Claude 上下文窗口 | https://platform.claude.com/docs/en/build-with-claude/context-windows
versions: tiktoken 0.14 · OpenAI Python SDK 3.42
seo_title: 大模型 token 是什么：计数、上下文窗口和费用计算
seo_description: 讲解大模型的 token 和上下文窗口：中英文各占多少 token、用 tiktoken 计数、读取 usage、估算费用、预留输出空间和裁剪对话历史。
---

## token 是什么 {#what}

模型不直接处理文字。文字先被切成 token，每个 token 对应词表里的一个编号，模型读写的都是这些编号。

token 既不是字符，也不是单词，切分方式由分词器决定。常见的英文单词是一个 token，中文一般两个字左右一个 token。

```python
import tiktoken

encoding = tiktoken.get_encoding("o200k_base")

def show(text: str) -> list[str]:
    return [encoding.decode([token]) for token in encoding.encode(text)]

show("Hello, world!")  # => ['Hello', ',', ' world', '!']
show("人工智能正在改变软件开发")  # => ['人工', '智能', '正在', '改变', '软件', '开发']
```

粗略估算时，英文约 4 个字符一个 token，中文约 1.5 到 2 个字符一个 token。

:::warn 每家模型的分词器不同
tiktoken 是 OpenAI 模型用的分词器。其他模型的切法不一样，用它计算的结果只能当估计值。精确数字要看接口返回的 `usage`，或者用服务商提供的计数接口，比如 Claude 的 `count_tokens`。
:::

## 读取用量 {#usage}

每次响应都带 `usage`，这才是实际计费的数字。

:::compare 读取 token 用量
```python
§ import fakellm
§ fakellm.serve("你好")
§ MODEL = "demo"
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "你好"}],
)

usage = response.usage
print(usage.prompt_tokens)  # => 12
print(usage.completion_tokens)  # => 5
print(usage.total_tokens)  # => 17
```
```java no-run
§ void run(OpenAIClient client, ChatCompletionCreateParams params) {
var response = client.chat().completions().create(params);

response.usage().ifPresent(usage -> {
    System.out.println(usage.promptTokens());
    System.out.println(usage.completionTokens());
    System.out.println(usage.totalTokens());
});
§ }
```
```kotlin no-run
§ fun run(client: OpenAIClient, params: ChatCompletionCreateParams) {
val response = client.chat().completions().create(params)

response.usage().ifPresent { usage ->
    println(usage.promptTokens())
    println(usage.completionTokens())
    println(usage.totalTokens())
}
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 字段 | `usage.prompt_tokens` | `usage.promptTokens()` | `usage.promptTokens()` |
| 可能为空 | 流式请求不打开时为 `None` | `Optional` | `Optional` |

> 要点: 把每次调用的用量记进数据库，出现异常费用时才查得出来。按用户统计还能用来限额。
:::

## 计算费用 {#cost}

输入和输出分开计价，输出通常贵好几倍。价格单位是每百万 token。

Agent 的费用常常超出预期：一次任务要调用很多轮模型，每一轮都带着完整的历史，输入 token 会累加。

```python
INPUT_PRICE = 2.0  # 元 / 百万 token，以服务商的价格表为准
OUTPUT_PRICE = 8.0

def cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE) / 1_000_000

# 一次问答
print(round(cost(1_000, 300), 4))  # => 0.0044

# 一个 Agent 跑 10 轮，每轮历史增加 1000 token
rounds = [cost(1_000 * (i + 1), 300) for i in range(10)]
print(round(sum(rounds), 4))  # => 0.134
```

上面的例子里，10 轮的费用是单次的 30 倍。下面三件事最能省钱：缩短历史、打开提示缓存、简单步骤换便宜的模型。

## 上下文窗口 {#window}

上下文窗口是模型一次能处理的 token 上限，输入和输出都算在内。超出时接口会报错，或者回答被截断。

`max_tokens` 限制这一次最多输出多少。这几个数字的关系是：

```text
输入 token + 输出 token ≤ 上下文窗口
输出 token ≤ max_tokens
```

输入快要占满窗口时，模型就没有空间写回答了，所以要给输出留出余量。

:::compare 限制输出长度
```python
§ import fakellm
§ fakellm.serve("这是一段被截")
§ MODEL = "demo"
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "写一篇长文"}],
    max_tokens=100,
)
print(response.choices[0].finish_reason)
```
```java no-run
§ static final String MODEL = "your-model";
§ void run() {
var params = ChatCompletionCreateParams.builder()
    .model(MODEL)
    .addUserMessage("写一篇长文")
    .maxTokens(100)
    .build();
§ }
```
```kotlin no-run
§ const val MODEL = "your-model"
§ fun run() {
val params = ChatCompletionCreateParams.builder()
    .model(MODEL)
    .addUserMessage("写一篇长文")
    .maxTokens(100)
    .build()
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 参数 | `max_tokens` | `.maxTokens()` | `.maxTokens()` |
| 被截断时 | `finish_reason == "length"` | = | = |

> 要点: OpenAI 的新模型要用 `max_completion_tokens`，其他兼容服务大多还是 `max_tokens`，以服务商文档为准。
:::

## 裁剪对话历史 {#trim}

对话越来越长时，最简单的做法是保留 `system` 和最近的消息，把最早的丢掉。

```python
import tiktoken

encoding = tiktoken.get_encoding("o200k_base")

def count(message: dict) -> int:
    return len(encoding.encode(message["content"])) + 4  # 每条消息有少量额外开销

def trim(messages: list[dict], limit: int) -> list[dict]:
    system, rest = messages[0], messages[1:]
    kept = []
    used = count(system)
    for message in reversed(rest):
        used += count(message)
        if used > limit:
            break
        kept.append(message)
    return [system, *reversed(kept)]

history = [
    {"role": "system", "content": "你是助手"},
    {"role": "user", "content": "第一个问题" * 20},
    {"role": "assistant", "content": "第一个回答" * 20},
    {"role": "user", "content": "第二个问题"},
]

[m["role"] for m in trim(history, 60)]  # => ['system', 'user']
```

这样做可能丢掉重要信息。「Agent 开发」大类的「记忆与上下文工程」一章会讲摘要和压缩。

:::warn 工具调用的消息不能拆开
裁剪历史时，一条带 `tool_calls` 的 `assistant` 消息和它对应的 `tool` 消息必须一起保留或一起删除。只留下其中一个，接口会返回 400。
:::

:::map token 概念对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `encoding.encode(text)` | jtokkit 的 `encode` | jtokkit 的 `encode` | 本地估算 token |
| `response.usage` | `response.usage()` | `response.usage()` | 实际计费数字 |
| `max_tokens` | `.maxTokens()` | `.maxTokens()` | 限制输出长度 |
| `finish_reason` | `choice.finishReason()` | `choice.finishReason()` | `length` 表示被截断 |
:::

:::recap
- token 是模型处理文字的单位，中文约两个字一个，每家分词器不同
- 实际用量以响应里的 `usage` 为准，记录下来才能追查费用
- 输入和输出分开计价，Agent 每轮都重发历史，费用累加很快
- 输入加输出不能超过上下文窗口，要给回答留出空间
- 超长时保留 `system` 和最近的消息，工具调用的消息要成对保留
:::
