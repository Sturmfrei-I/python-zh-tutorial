---
id: sampling
part: 调用模型
title: 采样参数
lede: 同样的问题问两次，答案可能不一样。这一章看模型怎么选下一个 token，以及 temperature、top_p 这些参数到底在调什么。
source: DeepSeek 温度设置 | https://api-docs.deepseek.com/zh-cn/quick_start/parameter_settings ; OpenAI API 参考 | https://developers.openai.com/api/reference/python/ ; Claude API 版本说明 | https://platform.claude.com/docs/en/api/versioning.md
versions: OpenAI Python SDK 3.42 · OpenAI Java SDK 4.95
seo_title: 大模型采样参数：temperature、top_p 和 seed 怎么设
seo_description: 用代码讲清 temperature 和 top_p 的原理，以及 max_tokens、stop、seed 的用法和不同场景的推荐设置，并说明新模型不再支持采样参数的情况。
---

## 模型怎么选下一个词 {#how}

模型每次只生成一个 token。它先给词表里每个 token 打分，再把分数转成概率，最后按概率抽一个。这就是回答不固定的原因。

采样参数调整的是最后这一步：概率怎么算，从哪些候选里抽。

## temperature {#temperature}

`temperature` 控制概率分布的集中程度。分数先除以温度，再转成概率：

- 温度小于 1：差距被放大，高分 token 几乎总是被选中，结果稳定
- 温度等于 1：保持模型原本的分布
- 温度大于 1：差距被缩小，低分 token 也有机会，结果更多样

下面用三个候选 token 算一下。

```python
import math

def probabilities(scores: list[float], temperature: float) -> list[float]:
    scaled = [score / temperature for score in scores]
    total = sum(math.exp(value) for value in scaled)
    return [round(math.exp(value) / total, 2) for value in scaled]

scores = [2.0, 1.0, 0.1]

probabilities(scores, 1.0)  # => [0.66, 0.24, 0.1]
probabilities(scores, 0.2)  # => [0.99, 0.01, 0.0]
probabilities(scores, 2.0)  # => [0.5, 0.3, 0.19]
```

温度为 0 时直接选最高分，同样的输入大概率得到同样的输出。但这不是绝对的，服务端的模型版本、硬件和负载均衡都可能带来差异。

## top_p {#top-p}

`top_p` 又叫核采样。它把 token 按概率从高到低排列，只保留累计概率刚好达到 `p` 的那一批，再从中抽取。低概率的 token 直接被排除。

```python
def top_p(probs: dict[str, float], p: float) -> dict[str, float]:
    kept = {}
    total = 0.0
    for token, prob in sorted(probs.items(), key=lambda item: -item[1]):
        kept[token] = prob
        total += prob
        if total >= p:
            break
    return {token: round(prob / total, 2) for token, prob in kept.items()}

candidates = {"晴": 0.6, "阴": 0.3, "雨": 0.08, "雪": 0.02}

top_p(candidates, 0.8)  # => {'晴': 0.67, '阴': 0.33}
top_p(candidates, 0.95)  # => {'晴': 0.61, '阴': 0.31, '雨': 0.08}
```

`temperature` 和 `top_p` 作用相似，一般只调一个。

## 其他常用参数 {#others}

:::compare 设置请求参数
```python
§ import fakellm
§ fakellm.serve("晴")
§ MODEL = "demo"
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "北京明天天气？"}],
    temperature=0.2,
    max_tokens=200,
    stop=["\n\n"],
    seed=42,
)
§ assert fakellm.requests[0]["temperature"] == 0.2
§ assert fakellm.requests[0]["stop"] == ["\n\n"]
```
```java no-run
§ static final String MODEL = "your-model";
§ void run() {
var params = ChatCompletionCreateParams.builder()
    .model(MODEL)
    .addUserMessage("北京明天天气？")
    .temperature(0.2)
    .maxTokens(200)
    .stopOfStrings(List.of("\n\n"))
    .seed(42)
    .build();
§ }
```
```kotlin no-run
§ const val MODEL = "your-model"
§ fun run() {
val params = ChatCompletionCreateParams.builder()
    .model(MODEL)
    .addUserMessage("北京明天天气？")
    .temperature(0.2)
    .maxTokens(200)
    .stopOfStrings(listOf("\n\n"))
    .seed(42)
    .build()
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 写法 | 关键字参数 | Builder 方法 | Builder 方法 |
| 不传时 | 用服务端默认值 | = | = |

> 要点: 不传就是用默认值。先用默认值，有明确问题时再调整，不要一开始就调参数。
:::

- `max_tokens`：限制输出长度。它只负责截断，不会让模型写得更简短。
- `stop`：遇到指定字符串就停止，结果里不包含这个字符串。
- `seed`：让采样尽量可重复。这是尽力而为，不是保证，换了模型版本结果就可能不同。
- `frequency_penalty`、`presence_penalty`：降低重复用词的概率，有的服务不支持。

## 不同场景怎么设 {#recommend}

| 场景 | 建议 | 原因 |
| --- | --- | --- |
| 工具调用、信息抽取 | 低温度或默认值 | 要稳定，不要发挥 |
| 代码生成 | 低温度 | 准确比多样重要 |
| 日常对话 | 默认值 | 服务商已经调过 |
| 创意写作 | 稍高的温度 | 需要多样性 |

具体数值要看服务商文档，同一个数字在不同模型上效果不同。比如 DeepSeek 的默认值是 1.0，文档建议代码生成用 0.0，创意写作用 1.5，而有些服务的取值上限就是 1。

:::warn 新模型正在取消这些参数
推理能力强的模型会先思考再回答，采样参数的作用越来越小。Anthropic 从 API 版本 `2026-10-21` 起移除了 `temperature`、`top_p` 和 `top_k`，发送就返回 400，改用 `effort` 控制投入程度。OpenAI 的部分推理模型同样不接受这些参数。

所以别让业务逻辑依赖 `temperature`。要稳定的输出，用结构化输出加校验，比调温度可靠得多。
:::

:::map 采样思路对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `temperature=0.2` | `.temperature(0.2)` | `.temperature(0.2)` | 概率分布的集中程度 |
| `top_p=0.9` | `.topP(0.9)` | `.topP(0.9)` | 只保留头部候选 |
| `seed=42` | `.seed(42)` | `.seed(42)` | 和 `Random(42)` 不同，只是尽量可重复 |
| `stop=[...]` | `.stopOfStrings(...)` | `.stopOfStrings(...)` | 提前结束 |
:::

:::recap
- 模型按概率逐个生成 token，所以回答不固定
- `temperature` 调概率分布的集中程度，`top_p` 排除低概率候选，一般只调一个
- `max_tokens` 只负责截断，`stop` 遇到指定内容就停止，`seed` 不保证完全可重复
- 先用默认值，抽取和工具调用用低温度
- 新模型正在取消采样参数，稳定性要靠结构化输出和校验
:::
