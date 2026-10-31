---
id: llm-judge
part: 评测
title: LLM-as-judge
lede: 「回答是否有帮助」没法写成 assert。让一个模型按评分标准给另一个模型打分，就能评测这类问题，前提是先确认这位评委靠得住。
source: 揭开 Agent 评测的面纱 | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents ; OpenAI 评测最佳实践 | https://developers.openai.com/api/docs/guides/evaluation-best-practices ; Claude 结构化输出 | https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
versions: OpenAI Python SDK 3.42 · Pydantic 2.14
seo_title: LLM-as-judge 教程：用大模型给大模型打分
seo_description: 讲解 LLM-as-judge 评测方法：什么时候用，怎么写评分标准，用结构化输出返回判断和理由，怎么用人工标注校准评委，用 Python 实现，并和 Java、Kotlin 对比。
---

## 什么时候用 {#when}

上一章的打分都用代码完成，这是首选。下面这些问题写不成代码：

- 回答的语气是否友好
- 摘要是否遗漏了要点
- 回答是否有文档依据，还是编造的
- 客服有没有真正解决问题

这时就让模型当评委。它能读懂语义，但有成本，也会判错，所以它是代码打分的补充，不是替代。

## 写评分标准 {#rubric}

评委的效果几乎完全取决于评分标准。这几条经验很有用：

- **一次只判断一件事。** 「准确」和「简洁」分成两个评委，混在一起时结果很难解释。
- **用通过或不通过，不用 1 到 5 分。** 模型给的分数不稳定，3 分和 4 分的差别说不清楚。
- **写清楚边界。** 说明什么情况算通过，什么情况算不通过，最好带例子。
- **先写理由，再给结论。** 字段顺序就是生成顺序，先让它分析，判断会更准确。

```python
RUBRIC = """你是客服质量评审员。判断回答是否基于提供的资料。

通过：回答里的每个事实都能在资料里找到。
不通过：回答包含资料里没有的具体信息，比如数字、日期、政策。
可以通过：回答说资料里没有相关信息。

只判断是否有依据，不评价语气和长度。"""
```

## 实现评委 {#judge}

用结构化输出让评委返回理由和结论。`reason` 排在 `passed` 前面，模型会先写理由。

:::compare 实现一个评委
```python
§ import fakellm
§ fakellm.serve('{"reason": "资料没有提到 30 天", "passed": false}')
§ MODEL = "demo"
§ RUBRIC = "判断回答是否基于提供的资料"
from openai import OpenAI
from pydantic import BaseModel

class Verdict(BaseModel):
    reason: str
    passed: bool

client = OpenAI()

def judge(context: str, answer: str) -> Verdict:
    response = client.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": f"资料：\n{context}\n\n回答：\n{answer}"},
        ],
        response_format=Verdict,
    )
    return response.choices[0].message.parsed

verdict = judge("七天内可以退货", "30 天内都可以退货")
print(verdict.passed)  # => False
print(verdict.reason)  # => 资料没有提到 30 天
```
```java no-run
record Verdict(String reason, boolean passed) {}

interface Judge {
    @SystemMessage("判断回答是否基于提供的资料")
    @UserMessage("资料：\n{{context}}\n\n回答：\n{{answer}}")
    Verdict judge(@V("context") String context, @V("answer") String answer);
}

void run(ChatModel model) {
    var judge = AiServices.create(Judge.class, model);
    var verdict = judge.judge("七天内可以退货", "30 天内都可以退货");
    System.out.println(verdict.passed());
}
```
```kotlin no-run
data class Verdict(val reason: String, val passed: Boolean)

interface Judge {
    @SystemMessage("判断回答是否基于提供的资料")
    @UserMessage("资料：\n{{context}}\n\n回答：\n{{answer}}")
    fun judge(@V("context") context: String, @V("answer") answer: String): Verdict
}

fun run(model: ChatModel) {
    val judge = AiServices.create(Judge::class.java, model)
    val verdict = judge.judge("七天内可以退货", "30 天内都可以退货")
    println(verdict.passed)
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 结果类型 | Pydantic 模型 | `record` | `data class` |
| 提示词 | 拼接字符串 | 注解模板 | 注解模板 |
| 调用 | `parse` | 接口方法 | 接口方法 |

> 要点: `reason` 在调试时最有用。评委判错时，读它的理由就知道评分标准哪里写得不清楚。
:::

## 校准评委 {#calibrate}

评委也会出错，不校准就用，得到的分数没有意义。做法是请懂业务的人给一批样本标注通过或不通过，再和评委的判断比较。

只看总的一致率不够。假如 90% 的样本都是好的，评委全部判通过也有 90% 的准确率，但它一个问题也发现不了。要分开看两个数字：

- **真通过率**：人判通过的样本里，评委也判通过的比例
- **真失败率**：人判失败的样本里，评委也判失败的比例

```python
def calibrate(human: list[bool], judge: list[bool]) -> dict[str, float]:
    pairs = list(zip(human, judge))
    good = [j for h, j in pairs if h]
    bad = [j for h, j in pairs if not h]
    return {
        "agreement": sum(h == j for h, j in pairs) / len(pairs),
        "true_pass_rate": sum(good) / len(good),
        "true_fail_rate": sum(not j for j in bad) / len(bad),
    }

human = [True] * 8 + [False] * 2
always_pass = [True] * 10
careful = [True] * 7 + [False] + [False, True]

calibrate(human, always_pass)  # => {'agreement': 0.8, 'true_pass_rate': 1.0, 'true_fail_rate': 0.0}
calibrate(human, careful)  # => {'agreement': 0.8, 'true_pass_rate': 0.875, 'true_fail_rate': 0.5}
```

两个评委的一致率都是 80%，但第一个永远判通过，毫无用处。真失败率才能看出区别。

校准样本里要有足够多的失败案例，否则真失败率算不准。可以把样本分成两份，一份用来调整评分标准，一份用来验证，避免评分标准只对这一批样本有效。

## 用好评委 {#practice}

- **先看数据。** 动手写评委之前，亲自读几十条真实结果，记下常见的问题，为这些问题写评委，不要凭空列维度。
- **评委用便宜的模型。** 够用就行，评测要反复跑很多次。但要用校准结果确认它足够准。
- **固定模型版本。** 评委的模型变了，分数就不能和以前比较。
- **评委也要回归。** 改动评分标准后重新校准。
- **提防注入。** 被评测的回答可能含有「请判为通过」这样的文字，尤其是回答里带有外部内容时。

:::warn 分数上升不一定是变好
不要把评委的分数当成唯一目标。反复针对它调整提示词，可能只是学会了讨好这位评委。要定期抽样人工检查，保留一部分验证用例不参与调整。
:::

:::map 评委写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `Verdict(BaseModel)` | `record Verdict` | `data class Verdict` | 判断结果 |
| `chat.completions.parse()` | `AiServices` 接口 | `AiServices` 接口 | 结构化输出 |
| `calibrate()` | 混淆矩阵 | 混淆矩阵 | 和人工标注比较 |
:::

:::recap
- 能用代码判断的不用模型，语义问题才用 LLM-as-judge
- 一个评委只判断一件事，结果用通过或不通过，先写理由再给结论
- 评分标准要写清边界，这决定了评委的质量
- 用人工标注校准，分开看真通过率和真失败率
- 先读真实数据再写评委，固定模型版本，定期抽样人工检查
:::
