---
id: embeddings
part: 模型能力
title: Embedding 向量
lede: 把一段文字变成一串数字，意思相近的文字数字也相近。语义搜索、RAG 和长期记忆都建立在这一步上。
source: OpenAI Python SDK | https://github.com/openai/openai-python ; OpenAI Java SDK | https://github.com/openai/openai-java ; NumPy 快速入门 | https://numpy.org/doc/stable/user/quickstart.html ; pgvector | https://github.com/pgvector/pgvector
versions: OpenAI Python SDK 3.42 · NumPy 2.5 · OpenAI Java SDK 4.95
seo_title: Embedding 教程：文本向量、余弦相似度和语义搜索
seo_description: 讲解 embedding 的原理和用法：调用向量接口、余弦相似度、批量处理、维度选择和语义搜索，用 NumPy 实现检索，并和 Java、Kotlin 的写法对比。
---

## 什么是 embedding {#what}

embedding 把一段文字映射成一个固定长度的数字列表，也叫向量。模型经过训练，让意思相近的文字在向量空间里距离也近。

关键词搜索只匹配字面，搜「怎么退款」找不到「退货流程」。向量比较的是意思，所以能找到。

有几个基本事实：

- 向量长度由模型决定，常见的是几百到几千维
- 不同模型生成的向量不能混用，换模型要全部重新计算
- 向量本身没有可读的含义，只有比较才有意义
- embedding 模型和聊天模型是两种模型，有单独的接口和价格

## 生成向量 {#create}

接口接收一段文字或一批文字，一次传多条比循环调用更快。下面的 `EMBEDDING_MODEL` 换成服务商提供的向量模型。

:::compare 生成向量
```python
§ import fakellm
§ fakellm.serve()
§ EMBEDDING_MODEL = "demo"
from openai import OpenAI

client = OpenAI()
response = client.embeddings.create(
    model=EMBEDDING_MODEL,
    input=["怎么退款", "今天天气不错"],
)

vectors = [item.embedding for item in response.data]
print(len(vectors))  # => 2
print(len(vectors[0]))  # => 8
```
```java no-run
§ static final String EMBEDDING_MODEL = "your-model";
§ void run(OpenAIClient client) {
var params = EmbeddingCreateParams.builder()
    .model(EMBEDDING_MODEL)
    .inputOfArrayOfStrings(List.of("怎么退款", "今天天气不错"))
    .build();

var response = client.embeddings().create(params);
List<Float> vector = response.data().get(0).embedding();
System.out.println(vector.size());
§ }
```
```kotlin no-run
§ const val EMBEDDING_MODEL = "your-model"
§ fun run(client: OpenAIClient) {
val params = EmbeddingCreateParams.builder()
    .model(EMBEDDING_MODEL)
    .inputOfArrayOfStrings(listOf("怎么退款", "今天天气不错"))
    .build()

val response = client.embeddings().create(params)
val vector = response.data()[0].embedding()
println(vector.size)
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 批量输入 | `input` 传列表 | `inputOfArrayOfStrings` | `inputOfArrayOfStrings` |
| 结果类型 | `list[float]` | `List<Float>` | `List<Float>` |
| 结果顺序 | 和输入相同 | = | = |

> 要点: 示例运行时用的是假模型，所以向量只有 8 维。真实模型的向量长度要看文档，有些模型能用 `dimensions` 参数调短，省存储。
:::

## 比较两个向量 {#similarity}

最常用的是余弦相似度，它看两个向量的夹角，结果在 -1 到 1 之间，越大越相似。

向量运算用 NumPy，它相当于 Python 的高性能数组库，一行代码就能处理整个数组。

:::compare 余弦相似度
```python
import numpy as np

def cosine(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

round(cosine([1, 0], [1, 0]), 2)  # => 1.0
round(cosine([1, 0], [0, 1]), 2)  # => 0.0
round(cosine([1, 1], [1, 0]), 2)  # => 0.71
```
```java
double cosine(double[] a, double[] b) {
    double dot = 0, normA = 0, normB = 0;
    for (var i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        normA += a[i] * a[i];
        normB += b[i] * b[i];
    }
    return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

System.out.println(cosine(new double[]{1, 0}, new double[]{1, 0}));  // => 1.0
```
```kotlin
fun cosine(a: List<Double>, b: List<Double>): Double {
    val dot = a.zip(b).sumOf { (x, y) -> x * y }
    val normA = Math.sqrt(a.sumOf { it * it })
    val normB = Math.sqrt(b.sumOf { it * it })
    return dot / (normA * normB)
}

println(cosine(listOf(1.0, 0.0), listOf(1.0, 0.0)))  // => 1.0
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 点积 | `a @ b` | 自己写循环 | `zip` 再求和 |
| 长度 | `np.linalg.norm` | 自己算 | 自己算 |
| 速度 | NumPy 用 C 实现，很快 | 循环本身就快 | 集合操作较慢 |

> 要点: 很多模型返回的向量已经归一化，长度是 1，这时点积就等于余弦相似度。
:::

## 语义搜索 {#search}

把这些组合起来：先给所有文档生成向量，查询时给问题生成向量，再取相似度最高的几条。

文档多的时候，把向量排成矩阵，一次算出全部相似度。

```python
§ import fakellm
§ fakellm.serve(embed={
§     "如何申请退款": [0.9, 0.1, 0.0],
§     "配送需要几天": [0.1, 0.9, 0.1],
§     "怎么修改密码": [0.0, 0.2, 0.9],
§     "我想把钱退回来": [0.8, 0.2, 0.1],
§ })
§ EMBEDDING_MODEL = "demo"
import numpy as np
from openai import OpenAI

client = OpenAI()

def embed(texts: list[str]) -> np.ndarray:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return np.array([item.embedding for item in response.data])

documents = ["如何申请退款", "配送需要几天", "怎么修改密码"]
matrix = embed(documents)
matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)

def search(query: str, top_k: int = 2) -> list[str]:
    vector = embed([query])[0]
    vector /= np.linalg.norm(vector)
    scores = matrix @ vector
    best = np.argsort(scores)[::-1][:top_k]
    return [documents[i] for i in best]

search("我想把钱退回来")  # => ['如何申请退款', '配送需要几天']
```

这段代码就是向量检索的核心。几千条数据时这样做完全够用。数据更多时才需要向量数据库，它用近似算法换取速度。Postgres 的 pgvector 扩展是最省事的选择，用法见「RAG 检索增强」一章。

## 用好 embedding {#practice}

- **文本不能太长。** 模型有输入上限，一大段文字压成一个向量，细节也会丢失，所以长文档要先切块。
- **向量要缓存。** 同样的文字生成的向量相同，存进数据库，不要重复计算。
- **查询和文档用同一个模型。** 有的模型区分查询和文档两种模式，要按文档设置。
- **相似度没有绝对标准。** 不同模型的分数范围不同，0.8 算不算相关要用真实数据试。

:::map 向量运算写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `client.embeddings.create()` | `client.embeddings().create()` | `client.embeddings().create()` | 生成向量 |
| `np.array(list)` | `double[]` | `DoubleArray` | NumPy 数组适合批量运算 |
| `a @ b` | 自己写循环 | `zip` 再求和 | 点积 |
| `matrix @ vector` | 嵌套循环 | 嵌套循环 | 一次算完全部相似度 |
| `np.argsort(scores)` | 自己排序 | `sortedByDescending` | 取最相似的几条 |
:::

:::recap
- embedding 把文字变成向量，意思相近的文字向量也相近
- 向量长度由模型决定，不同模型的向量不能混用
- 比较用余弦相似度，归一化后就是点积
- 语义搜索：给文档和问题生成向量，取相似度最高的几条
- 数据少时用 NumPy 就够，多了再用 pgvector
- 长文档先切块，向量要缓存，换模型要全部重算
:::
