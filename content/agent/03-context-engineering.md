---
id: context-engineering
part: Agent 基础
title: 记忆与上下文工程
lede: 上下文窗口是 Agent 最稀缺的资源。放什么、丢什么、什么时候压缩，决定了它跑到第 50 步时还清不清醒。
source: 上下文工程 | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ; Claude 上下文压缩 | https://platform.claude.com/docs/en/build-with-claude/compaction ; LangChain4j 聊天记忆 | https://docs.langchain4j.dev/tutorials/chat-memory ; LangGraph 记忆 | https://docs.langchain.com/oss/python/langgraph/memory
versions: OpenAI Python SDK 3.42 · SQLModel 0.0.48 · LangChain4j 1.23
seo_title: Agent 记忆和上下文工程：智能体的上下文管理
seo_description: 讲解 AI Agent 智能体的上下文管理：清理工具结果、摘要压缩、短期记忆、长期记忆、笔记和子 Agent 隔离，用 Python 实现，并和 LangChain4j 的 ChatMemory 对比。
---

## 上下文里有什么 {#what}

提示词工程关心怎么写好一段提示。上下文工程关心的是每一轮到底让模型看到什么。Agent 的上下文由这些内容组成：

- 系统提示和工具定义
- 用户消息和模型回答
- 工具调用的结果，这部分通常涨得最快
- 检索到的文档
- 从长期记忆里取出的内容

模型的注意力有限。上下文太长不仅费钱，模型表现也会变差，所以目标是用尽量少的 token 提供正确的信息。

## 清理工具结果 {#clear}

最容易做、效果也最好的一步，是清理旧的工具结果。模型已经读过的日志和网页，后面很少再用得上。

保留调用记录，把内容换成一句占位符。这样消息的结构不变，不会破坏 `tool_call_id` 的对应关系。

```python
def clear_old_results(messages: list[dict], keep: int = 2) -> list[dict]:
    tool_indexes = [i for i, m in enumerate(messages) if m["role"] == "tool"]
    old = set(tool_indexes[:-keep]) if keep else set(tool_indexes)
    return [
        {**m, "content": "（旧结果已清除）"} if i in old else m
        for i, m in enumerate(messages)
    ]

messages = [
    {"role": "user", "content": "分析日志"},
    {"role": "tool", "tool_call_id": "1", "content": "很长的日志 A"},
    {"role": "tool", "tool_call_id": "2", "content": "很长的日志 B"},
    {"role": "tool", "tool_call_id": "3", "content": "很长的日志 C"},
]

[m["content"] for m in clear_old_results(messages, keep=1)]  # => ['分析日志', '（旧结果已清除）', '（旧结果已清除）', '很长的日志 C']
```

工具结果在进入上下文之前也要处理：截断过长的输出，告诉模型总共有多少内容，需要时可以分页读取。

修改已有消息会破坏提示缓存的前缀。所以不要每一轮都清理，等上下文接近上限时一次清理一批。

## 压缩历史 {#compact}

只清理工具结果还不够时，就让模型把早期对话总结成一段话，用它代替原来的消息。

总结要保留这些内容：用户的目标和约束、已经做出的决定、改过的文件、还没完成的事。可以丢掉的是过程中的试错和工具的原始输出。

:::compare 限制记忆长度
```python
§ import fakellm
§ fakellm.serve("用户想做退款功能，已确定用 FastAPI")
§ MODEL = "demo"
from openai import OpenAI

client = OpenAI()

SUMMARY_PROMPT = """总结下面的对话，保留用户目标、约束、
已做的决定和未完成的事，省略试错过程。"""

def compact(messages: list[dict], keep: int = 4) -> list[dict]:
    system, old, recent = messages[0], messages[1:-keep], messages[-keep:]
    if not old:
        return messages
    text = "\n".join(f"{m['role']}: {m['content']}" for m in old)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    summary = response.choices[0].message.content
    return [system, {"role": "user", "content": f"之前的对话摘要：{summary}"}, *recent]

history = [{"role": "system", "content": "你是助手"}]
history += [{"role": "user", "content": f"消息 {i}"} for i in range(8)]

result = compact(history)
print(len(result))  # => 6
print(result[1]["content"])  # => 之前的对话摘要：用户想做退款功能，已确定用 FastAPI
```
```java no-run
interface Assistant {
    String chat(@MemoryId String userId, @UserMessage String text);
}

void run(ChatModel model) {
    var assistant = AiServices.builder(Assistant.class)
        .chatModel(model)
        .chatMemoryProvider(userId ->
            MessageWindowChatMemory.withMaxMessages(20))
        .build();

    assistant.chat("ada", "我想做退款功能");
}
```
```kotlin no-run
interface Assistant {
    fun chat(@MemoryId userId: String, @UserMessage text: String): String
}

fun run(model: ChatModel) {
    val assistant = AiServices.builder(Assistant::class.java)
        .chatModel(model)
        .chatMemoryProvider { MessageWindowChatMemory.withMaxMessages(20) }
        .build()

    assistant.chat("ada", "我想做退款功能")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 窗口裁剪 | 自己写 | `MessageWindowChatMemory` | `MessageWindowChatMemory` |
| 按 token 裁剪 | 自己写 | `TokenWindowChatMemory` | `TokenWindowChatMemory` |
| 摘要压缩 | 自己写 | 自己写 | 自己写 |
| 按用户隔离 | 按会话保存消息列表 | `@MemoryId` | `@MemoryId` |

> 要点: 框架提供的窗口记忆只是丢弃旧消息。需要保留要点时，要自己实现摘要，或者用服务商提供的压缩功能。
:::

压缩的时机一般设在上下文用到 70% 到 80% 时。太早浪费信息，太晚可能来不及。切分点不能落在工具调用和它的结果之间，否则接口会报错。

Claude 等服务也提供了服务端压缩。用上它们之后要注意，返回的压缩内容必须原样传回下一次请求。

## 短期记忆和长期记忆 {#memory}

短期记忆就是当前会话的消息列表，会话结束就没有了。长期记忆跨会话保存，比如用户的偏好和项目信息。

| 类型 | 范围 | 存在哪 | 对应的 Android 概念 |
| --- | --- | --- | --- |
| 短期记忆 | 一次会话 | 消息列表，存数据库或 Redis | `ViewModel` |
| 长期记忆 | 跨会话 | 数据库或向量库 | Room |
| 工作笔记 | 一次长任务 | 文件或数据库 | 临时文件 |

长期记忆有两种写入方式。一种是给模型一个工具，由它决定记什么。另一种是对话结束后用另一次模型调用提取要点。

```python
§ import json
§ from openai import OpenAI
from sqlmodel import Field, Session, SQLModel, create_engine, select

class Memory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    fact: str

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)

def remember(user_id: str, fact: str) -> str:
    """保存关于用户的长期信息，比如偏好和背景"""
    with Session(engine) as session:
        session.add(Memory(user_id=user_id, fact=fact))
        session.commit()
    return "已保存"

def recall(user_id: str) -> list[str]:
    with Session(engine) as session:
        rows = session.exec(select(Memory).where(Memory.user_id == user_id))
        return [row.fact for row in rows]

def system_prompt(user_id: str) -> str:
    facts = "\n".join(f"- {fact}" for fact in recall(user_id))
    return f"你是助手。关于这位用户你知道：\n{facts}"

remember("ada", "喜欢简短的回答")
print(system_prompt("ada"))
```
```output
你是助手。关于这位用户你知道：
- 喜欢简短的回答
```

记忆多了以后，不能全部塞进上下文，要用 embedding 检索出和当前问题相关的几条，方法见「RAG 检索增强」一章。

:::warn 记忆也有风险
记忆会过期，用户换了工作，旧的记录就是错的，所以要能修改和删除，最好记录写入时间。

记忆还可能被污染。如果 Agent 读到的网页让它保存了一条恶意指令，这条指令以后每次都会被读出来。写入长期记忆的内容要限制来源，不要把外部内容原样存进去。
:::

## 笔记和子 Agent {#isolate}

长任务里还有两个办法能让上下文保持干净。

**写笔记。** 让 Agent 把进度写进文件或数据库，比如任务清单和已知结论，上下文被压缩后再读回来。信息存在外面，不占窗口。

**子 Agent。** 主 Agent 把一个子任务交给新的 Agent，子 Agent 有自己干净的上下文，读完几十个文件后只返回一段结论。主 Agent 的上下文里只多了这段话。

```python
§ import fakellm
§ fakellm.serve("认证模块在 auth.py，使用 JWT")
§ MODEL = "demo"
§ from openai import OpenAI
§ client = OpenAI()
def run_subagent(task: str) -> str:
    """把调研任务交给子 Agent，只返回结论"""
    messages = [
        {"role": "system", "content": "完成任务后用几句话汇报结论"},
        {"role": "user", "content": task},
    ]
    response = client.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content

# 主 Agent 的工具结果只有这一段话，中间的过程不进入主上下文
print(run_subagent("调研项目的认证是怎么实现的"))  # => 认证模块在 auth.py，使用 JWT
```

这里为了简短只调用了一次模型，真实的子 Agent 就是「工具调用循环」一章的循环。

子 Agent 适合调研这类读多写少的任务。多个 Agent 同时改同一批文件容易冲突，这种情况要串行执行。

:::map 记忆写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| 消息列表 | `ChatMemory` | `ChatMemory` | 短期记忆 |
| 自己裁剪 | `MessageWindowChatMemory` | `MessageWindowChatMemory` | 按条数保留 |
| `tiktoken` 计数后裁剪 | `TokenWindowChatMemory` | `TokenWindowChatMemory` | 按 token 保留 |
| 数据库表 | `ChatMemoryStore` | `ChatMemoryStore` | 持久化 |
| 按 `user_id` 查询 | `@MemoryId` | `@MemoryId` | 区分用户 |
:::

:::recap
- 上下文工程决定每一轮让模型看到什么，内容越精确越好
- 先清理旧的工具结果，这一步最省事，效果也最好
- 接近上限时压缩历史，保留目标、决定和未完成的事
- 短期记忆是消息列表，长期记忆存数据库，按需检索后放进上下文
- 记忆会过期，也会被污染，要能修改，并限制写入来源
- 长任务用笔记保存进度，用子 Agent 隔离调研过程
:::
