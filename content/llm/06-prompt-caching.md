---
id: prompt-caching
part: 模型能力
title: 提示缓存
lede: Agent 每一轮都把同样的历史再发一遍，提示缓存让这部分内容便宜到十分之一甚至更低。用好它，主要看消息怎么排列。
source: OpenAI 提示缓存 | https://developers.openai.com/api/docs/guides/prompt-caching ; Claude 提示缓存 | https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md ; DeepSeek 上下文硬盘缓存 | https://api-docs.deepseek.com/zh-cn/guides/kv_cache
versions: OpenAI Python SDK 3.42 · 各服务商文档截至 2026 年 10 月
seo_title: Prompt Caching 教程：大模型提示缓存原理和用法
seo_description: 讲解 Prompt Caching 的前缀匹配原理、OpenAI、Claude、DeepSeek 的用法和价格差异、怎么安排消息顺序、怎么确认命中，以及常见的缓存失效原因。
---

## 缓存的是什么 {#what}

模型处理输入时要做大量计算。如果一次请求的开头和之前某次请求完全相同，服务端可以复用那部分计算结果，这就是提示缓存。

要记住两点：

- **它是前缀匹配。** 从第一个 token 开始逐个比较，遇到第一个不同的地方就停止，后面的内容全部按原价计算。
- **它缓存的是输入，不是回答。** 模型每次仍然会重新生成回答，输出质量不受影响。

Agent 特别适合缓存。一次任务里，系统提示、工具定义和历史消息一轮轮累积，每次请求都只在末尾增加一点内容。

## 消息要这样排 {#order}

因为是前缀匹配，稳定的内容必须放在前面，变化的内容放在后面。下面比较两种写法，`commonprefix` 算出的就是能命中缓存的长度。

```python
import os.path

RULES = "你是客服助手，请遵守以下规则：" + "不要编造信息。" * 100

def shared(a: str, b: str) -> int:
    return len(os.path.commonprefix([a, b]))

# 把时间放在最前面，每次请求都从第一个字开始不同
bad_a = f"现在是 10:01。\n{RULES}\n用户：退货"
bad_b = f"现在是 10:02。\n{RULES}\n用户：退货"

# 时间放在最后，规则部分都能命中
good_a = f"{RULES}\n现在是 10:01。\n用户：退货"
good_b = f"{RULES}\n现在是 10:02。\n用户：退货"

print(shared(bad_a, bad_b))  # => 8
print(shared(good_a, good_b) > len(RULES))  # => True
```

一个对缓存友好的 Agent 要做到这些：

- 工具定义和系统提示固定不变，放在最前面
- 当前时间、用户信息这些会变的内容放在最后一条消息里
- 工具的顺序固定，序列化 JSON 时用 `sort_keys=True`
- 只在消息列表末尾追加，不修改已有的消息

:::warn 这些写法会悄悄破坏缓存
系统提示里放 `datetime.now()` 或请求编号；每次用 `set` 遍历工具，导致顺序不固定；裁剪历史时删掉开头的消息。这些都不会报错，只是缓存命中率变成 0，账单变高。
:::

## 各家的差异 {#providers}

原理相同，用法和价格差别很大。下面是 2026 年 10 月的情况，用之前要再查一下文档。

| 对比项 | OpenAI | Claude | DeepSeek |
| --- | --- | --- | --- |
| 开启方式 | 自动 | 加 `cache_control` | 自动 |
| 最小长度 | 1024 token 左右 | 512 到 4096 token，看模型 | 没有公布 |
| 保留时间 | 新模型默认 30 分钟，可设 12 小时 | 默认 5 分钟，可设 1 小时 | 几小时到几天，不保证 |
| 命中价格 | 新模型是输入价的 0.1 倍，部分更低 | 输入价的 0.1 倍，部分新模型更低 | 比普通输入便宜很多 |
| 写入价格 | 新模型 1.25 倍起 | 1.25 倍起 | 按普通输入计费 |
| 看命中情况 | `cached_tokens` | `cache_read_input_tokens` | `prompt_cache_hit_tokens` |

Claude 需要在请求里声明缓存。最简单的做法是在顶层加一个 `cache_control`，缓存点会随着对话向后移动。缓存顺序是 `tools`、`system`、`messages`，改动前面的内容，后面的缓存全部失效。

```json
{
  "model": "your-model",
  "max_tokens": 1024,
  "cache_control": {"type": "ephemeral"},
  "system": "很长的系统提示……",
  "messages": [{"role": "user", "content": "你好"}]
}
```

## 确认命中 {#verify}

响应的 `usage` 里能看到命中了多少。缓存有没有生效，一定要看这个数字，不能靠猜。

:::compare 读取缓存命中数
```python
§ import fakellm
§ fakellm.USAGE = {**fakellm.USAGE, "prompt_tokens_details": {"cached_tokens": 1024}}
§ fakellm.serve("你好")
§ MODEL = "demo"
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "你好"}],
)

details = response.usage.prompt_tokens_details
print(details.cached_tokens)  # => 1024
```
```java no-run
§ void run(OpenAIClient client, ChatCompletionCreateParams params) {
var response = client.chat().completions().create(params);

var cached = response.usage()
    .flatMap(usage -> usage.promptTokensDetails())
    .flatMap(details -> details.cachedTokens())
    .orElse(0L);
System.out.println(cached);
§ }
```
```kotlin no-run
§ fun run(client: OpenAIClient, params: ChatCompletionCreateParams) {
val response = client.chat().completions().create(params)

val cached = response.usage()
    .flatMap { it.promptTokensDetails() }
    .flatMap { it.cachedTokens() }
    .orElse(0L)
println(cached)
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 字段 | `usage.prompt_tokens_details` | `usage.promptTokensDetails()` | `usage.promptTokensDetails()` |
| 可能为空 | 要先判断 `None` | `Optional` | `Optional` |

> 要点: 兼容服务的字段名不一样，DeepSeek 直接放在 `usage.prompt_cache_hit_tokens`。把命中率写进监控，改动提示词后马上就能看到影响。
:::

## 算一笔账 {#saving}

用前面的数字估算一下。假设 Agent 跑 10 轮，每轮多 1000 token 的历史，命中部分按 0.1 倍计价。

```python
PRICE = 2.0  # 元 / 百万 token

def input_cost(rounds: int, cached: bool) -> float:
    total = 0.0
    for i in range(rounds):
        tokens = 1_000 * (i + 1)
        hit = 1_000 * i if cached else 0
        total += (tokens - hit + hit * 0.1) * PRICE / 1_000_000
    return round(total, 4)

print(input_cost(10, cached=False))  # => 0.11
print(input_cost(10, cached=True))  # => 0.029
```

输入费用降到原来的四分之一左右，轮数越多，省得越多。这只是粗略估算，没有计入写入加价和未命中的情况。

:::recap
- 提示缓存复用相同前缀的计算结果，不缓存回答，不影响输出
- 它是前缀匹配，稳定内容放前面，变化内容放后面
- 工具顺序要固定，只在末尾追加，不改已有的消息
- OpenAI 和 DeepSeek 自动开启，Claude 要加 `cache_control`
- 看 `usage` 里的命中数，不要靠猜
:::
