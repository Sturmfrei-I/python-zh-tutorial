---
id: sse
part: Web 服务
title: SSE 流式响应
lede: 大模型的回答能一个字一个字地出现，靠的就是 SSE。这一章先看协议格式，再用 FastAPI 把事件发出去，最后处理报错和断线。
source: FastAPI 的 SSE 支持 | https://fastapi.tiangolo.com/zh/tutorial/server-sent-events/ ; 使用服务器发送事件 | https://developer.mozilla.org/zh-CN/docs/Web/API/Server-sent_events/Using_server-sent_events ; HTML 标准 | https://html.spec.whatwg.org/multipage/server-sent-events.html ; HTTPX 异步客户端 | https://www.python-httpx.org/async/
versions: FastAPI 0.162 · HTTPX 0.28 · Spring Boot 4.1 · OkHttp SSE 5.5
seo_title: FastAPI SSE 教程：流式输出大模型回答，对比 Spring
seo_description: 用 FastAPI 实现 SSE 流式响应：事件格式、异步生成器、ServerSentEvent、流式调用大模型、错误处理和断线重连，并和 Spring SseEmitter、Kotlin Flow、OkHttp SSE 对比。
---

## 为什么用 SSE {#why}

大模型生成一段回答要几秒到几十秒。如果等全部生成完再返回，用户只能对着空白页面等待。SSE（Server-Sent Events）让服务端在一个 HTTP 响应里持续写入事件，客户端边收边显示。

服务端向客户端推送数据，常见的有三种做法：

- **轮询**：客户端定时发请求询问。实现简单，但延迟高，大部分请求都是空跑。
- **SSE**：一个 HTTP 响应持续下发数据，方向是服务端到客户端。用的是普通 HTTP，代理和负载均衡都容易支持。
- **WebSocket**：升级成双向长连接，适合聊天室、协同编辑这类双方都频繁发消息的场景。

调用大模型的过程是发一个请求，收一串片段，只需要单向推送，所以 OpenAI 和 Anthropic 的流式接口都用 SSE。

## 事件格式 {#format}

SSE 的响应类型是 `text/event-stream`，内容是一行行的文本，空行表示一个事件结束。

```text
event: delta
id: 1
data: {"text":"你"}

data: {"text":"好"}

: 以冒号开头的是注释，常用来保持连接

event: done
data: [DONE]

```

- `data`：事件内容。一个事件有多行 `data` 时，客户端用换行符把它们拼起来
- `event`：事件类型，不写时类型是 `message`
- `id`：事件编号，断线重连时客户端会带回来
- `retry`：建议的重连等待时间，单位是毫秒

## 异步生成器 {#generator}

FastAPI 用异步生成器产生事件。函数里同时有 `async def` 和 `yield` 时就是异步生成器，每次 `yield` 交出一个值，消费方用 `async for` 读取。它和 Kotlin 的 `Flow` 几乎一一对应，Java 里最接近的是 Reactor 的 `Flux`。

:::compare 异步数据流
```python
import asyncio

async def count(n: int):
    for i in range(n):
        await asyncio.sleep(0.01)
        yield i

async def main():
    return [value async for value in count(3)]

asyncio.run(main())  # => [0, 1, 2]
```
```java no-run
Flux<Integer> count(int n) {
    return Flux.range(0, n)
        .delayElements(Duration.ofMillis(10));
}

void main() {
    System.out.println(count(3).collectList().block());  // [0, 1, 2]
}
```
```kotlin no-run
fun count(n: Int): Flow<Int> = flow {
    for (i in 0 until n) {
        delay(10)
        emit(i)
    }
}

fun main() = runBlocking {
    println(count(3).toList())  // [0, 1, 2]
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 定义 | `async def` 里写 `yield` | 用 `Flux` 的操作符组合 | `flow { emit() }` |
| 消费 | `async for` | `subscribe` | `collect` |
| 惰性 | 开始消费时才运行 | = | = |
| 速度匹配 | 消费方取走一个，生成方才继续 | 消费方用 `request(n)` 声明需求 | = |

> 要点: 记住「`yield` 对应 `emit`，`async for` 对应 `collect`」就够写接口了。`Flux` 靠操作符组合，写起来不像普通循环。
:::

## 用 FastAPI 发送事件 {#server}

接口写成异步生成器，再指定 `response_class=EventSourceResponse`，FastAPI 就把每次 `yield` 的值编码成一个事件。

:::compare 在服务端发送事件
```python
§ from fastapi.testclient import TestClient
import asyncio
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

app = FastAPI()

class Delta(BaseModel):
    text: str

@app.get("/stream", response_class=EventSourceResponse)
async def stream() -> AsyncIterable[Delta]:
    for word in ["你", "好"]:
        await asyncio.sleep(0.01)
        yield Delta(text=word)

§ body = TestClient(app).get("/stream").text.strip()
§ assert body == 'data: {"text":"你"}\n\ndata: {"text":"好"}'
```
```java no-run
§ Executor executor;
record Delta(String text) {}

@GetMapping("/stream")
SseEmitter stream() {
    var emitter = new SseEmitter();
    executor.execute(() -> {
        try {
            for (var word : List.of("你", "好")) {
                emitter.send(new Delta(word));
            }
            emitter.complete();
        } catch (IOException e) {
            emitter.completeWithError(e);
        }
    });
    return emitter;
}
```
```kotlin no-run
§ import org.springframework.web.bind.annotation.GetMapping
§ import org.springframework.web.servlet.mvc.method.annotation.SseEmitter
§ import java.io.IOException
§ import java.util.concurrent.Executor
§ lateinit var executor: Executor
data class Delta(val text: String)

@GetMapping("/stream")
fun stream(): SseEmitter {
    val emitter = SseEmitter()
    executor.execute {
        try {
            for (word in listOf("你", "好")) {
                emitter.send(Delta(word))
            }
            emitter.complete()
        } catch (e: IOException) {
            emitter.completeWithError(e)
        }
    }
    return emitter
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 写法 | 异步生成器，`yield` 一个事件 | 另开线程调用 `emitter.send` | 另开线程调用 `emitter.send` |
| 序列化 | Pydantic | Jackson | Jackson |
| 结束 | 函数返回 | 调用 `complete()` | 调用 `complete()` |
| 空闲保活 | 自动发送 | 自己发送 | 自己发送 |

> 要点: 生成器把事件的产生和发送放在一个函数里，不用自己管线程和收尾。
:::

响应内容和前面讲的格式一致：

```text
data: {"text":"你"}

data: {"text":"好"}
```

`-> AsyncIterable[Delta]` 不是必须的，但写上之后 FastAPI 会用 Pydantic 校验和序列化每个事件，速度更快，接口文档也更完整。

FastAPI 还会替你做三件事：加上 `Cache-Control: no-cache` 防止缓存，加上 `X-Accel-Buffering: no` 防止 Nginx 缓冲，空闲 15 秒时发送 `: ping` 注释，防止代理断开连接。

要设置事件类型或编号时，改为 `yield` 一个 `ServerSentEvent`。

```python
§ from collections.abc import AsyncIterable
§ from fastapi import FastAPI
§ from fastapi.testclient import TestClient
§ app = FastAPI()
from fastapi.sse import EventSourceResponse, ServerSentEvent

@app.get("/events", response_class=EventSourceResponse)
async def events() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"count": 1}, event="delta", id="1")
    yield ServerSentEvent(raw_data="[DONE]", event="done")

§ client = TestClient(app)
print(client.get("/events").text.strip())
```
```output
event: delta
data: {"count": 1}
id: 1

event: done
data: [DONE]
```

`data` 总是按 JSON 编码，字符串也会带上引号，中文会转义成 `\uXXXX`，客户端解析 JSON 后和原文相同。`raw_data` 原样发送，常用来发 `[DONE]` 这样的结束标记。

## 流式转发大模型的回答 {#llm}

大模型的接口要传提示词，所以一般用 POST。SSE 不限制请求方法，浏览器自带的 `EventSource` 才只支持 GET。

下面的 `call_model` 是一个假的模型，真实项目里换成大模型 SDK 的流式调用，接口的写法不变。

```python
§ from fastapi.testclient import TestClient
import asyncio
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

app = FastAPI()

class Prompt(BaseModel):
    text: str

async def call_model(prompt: str) -> AsyncIterable[str]:
    for word in ["Hello", ", ", "world"]:
        await asyncio.sleep(0.01)
        yield word

@app.post("/chat", response_class=EventSourceResponse)
async def chat(prompt: Prompt) -> AsyncIterable[ServerSentEvent]:
    try:
        async for delta in call_model(prompt.text):
            yield ServerSentEvent(data={"text": delta}, event="delta")
    except Exception:
        yield ServerSentEvent(data={"message": "生成失败"}, event="error")
    else:
        yield ServerSentEvent(raw_data="[DONE]", event="done")

§ client = TestClient(app)
print(client.post("/chat", json={"text": "hi"}).text.strip())
```
```output
event: delta
data: {"text": "Hello"}

event: delta
data: {"text": ", "}

event: delta
data: {"text": "world"}

event: done
data: [DONE]
```

:::warn 响应开始后就不能再改状态码
状态码在流开始时就发出去了，所以流里的错误要用事件告诉客户端。如果异常直接抛出去，客户端看到的只是连接中断，不知道发生了什么。

生成器里的 `HTTPException` 也不起作用，即使写在第一个 `yield` 之前，客户端收到的也是状态码 200 和空内容。鉴权和资源检查要放进 `Depends`，它在流开始之前运行，能正常返回 401、404。
:::

## 在客户端读取 {#client}

Python 里用 HTTPX 的 `stream` 逐行读取响应。默认的读取超时只有 5 秒，大模型思考的时间可能更长，流式请求要把超时调大。Android 上可以用 OkHttp 的 SSE 模块，再用 `callbackFlow` 包成 `Flow`。

:::compare 读取事件流
```python
§ import asyncio
§ from collections.abc import AsyncIterable
§ from fastapi import FastAPI
§ from fastapi.sse import EventSourceResponse, ServerSentEvent
§ app = FastAPI()
§ @app.post("/chat", response_class=EventSourceResponse)
§ async def chat() -> AsyncIterable[ServerSentEvent]:
§     yield ServerSentEvent(data={"text": "Hello"}, event="delta")
§     yield ServerSentEvent(data={"text": ", world"}, event="delta")
§     yield ServerSentEvent(raw_data="[DONE]", event="done")
import json

import httpx

async def read_answer(client: httpx.AsyncClient) -> str:
    answer = ""
    event = "message"
    async with client.stream("POST", "/chat") as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            field, _, value = line.partition(": ")
            if field == "event":
                event = value
            elif field == "data" and event == "delta":
                answer += json.loads(value)["text"]
    return answer

§ async def main():
§     transport = httpx.ASGITransport(app=app)
§     async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
§         print(await read_answer(client))  # => Hello, world
§ asyncio.run(main())
```
```java no-run
§ import java.net.http.HttpRequest;
String readAnswer(HttpClient client, HttpRequest request)
        throws Exception {
    var mapper = new ObjectMapper();
    var answer = new StringBuilder();
    var event = "message";
    var lines = client.send(request, BodyHandlers.ofLines()).body();
    for (var line : (Iterable<String>) lines::iterator) {
        if (line.startsWith("event: ")) {
            event = line.substring(7);
        } else if (line.startsWith("data: ") && event.equals("delta")) {
            var json = mapper.readTree(line.substring(6));
            answer.append(json.get("text").asText());
        }
    }
    return answer.toString();
}
```
```kotlin no-run
fun answers(
    client: OkHttpClient,
    request: Request,
): Flow<String> = callbackFlow {
    val listener = object : EventSourceListener() {
        override fun onEvent(
            eventSource: EventSource,
            id: String?,
            type: String?,
            data: String,
        ) {
            when (type) {
                "delta" -> trySend(data)
                "done" -> close()
            }
        }

        override fun onFailure(
            eventSource: EventSource,
            t: Throwable?,
            response: Response?,
        ) {
            close(t)
        }
    }
    val source = EventSources.createFactory(client)
        .newEventSource(request, listener)
    awaitClose { source.cancel() }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 读取方式 | 自己按行解析 | = | 回调 `onEvent` |
| 对外接口 | 异步函数或异步生成器 | 阻塞方法 | `Flow` |
| 自动重连 | 不支持 | = | = |
| 超时 | 创建客户端时用 `timeout` 调大 | 在请求上设置 `timeout` | 用 `readTimeout` 调大 |

> 要点: 自己解析只要十几行。项目里想省事可以用 `httpx-sse`。OkHttp 的 SSE 模块目前还标注为实验性功能。
:::

浏览器里的 `EventSource` 会自动重连，但只支持 GET，也不能自定义请求头。所以网页调用大模型接口时，一般用 `fetch` 读取响应流。

## 断开和重连 {#reconnect}

用户关掉页面或点了停止，连接就断开了。FastAPI 会取消生成器，正在等待的 `await` 处抛出 `asyncio.CancelledError`。这时应该停止调用大模型，否则会继续消耗 token。

取消本身不需要处理，清理工作写进 `finally` 就行。`CancelledError` 不是 `Exception` 的子类，前面的 `except Exception` 不会把它吞掉。

```python
§ import asyncio
§ from collections.abc import AsyncIterable
§ from fastapi import FastAPI
§ from fastapi.sse import EventSourceResponse
§ from fastapi.testclient import TestClient
§ app = FastAPI()
@app.get("/stream", response_class=EventSourceResponse)
async def stream() -> AsyncIterable[dict]:
    try:
        for i in range(3):
            await asyncio.sleep(0.01)
            yield {"count": i}
    finally:
        print("清理资源")  # 正常结束和连接断开时都会运行

§ TestClient(app).get("/stream")
```
```output
清理资源
```

依赖项的清理代码在响应结束后运行，所以流式接口用到的 `Depends` 资源会一直占用到流结束。

`id` 字段用来续传。重连时客户端把最后收到的编号放进 `Last-Event-ID` 请求头，服务端从下一条继续发送。

```python
§ from collections.abc import AsyncIterable
§ from typing import Annotated
§ from fastapi import FastAPI, Header
§ from fastapi.sse import EventSourceResponse, ServerSentEvent
§ from fastapi.testclient import TestClient
§ app = FastAPI()
ITEMS = ["a", "b", "c"]

@app.get("/items", response_class=EventSourceResponse)
async def items(
    last_event_id: Annotated[int | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    start = 0 if last_event_id is None else last_event_id + 1
    for i in range(start, len(ITEMS)):
        yield ServerSentEvent(data=ITEMS[i], id=str(i))

§ client = TestClient(app)
print(client.get("/items", headers={"Last-Event-ID": "1"}).text.strip())
```
```output
data: "c"
id: 2
```

续传的前提是服务端保存了已发送的内容。大模型的回答是边生成边发的，要支持续传，就得把事件先写进数据库或队列。多数应用选择断线后提示用户重新发送。

:::recap
- SSE 是一个持续写入的 HTTP 响应，事件之间用空行分隔
- 异步生成器的 `yield` 对应 `Flow` 的 `emit`，`async for` 对应 `collect`，Spring 里用 `SseEmitter` 或 `Flux`
- 接口写成异步生成器，加上 `response_class=EventSourceResponse`
- 要设置事件类型和编号时 `yield` 一个 `ServerSentEvent`
- 流开始后不能改状态码：错误用事件发送，鉴权放进 `Depends`
- 连接断开时生成器会被取消，清理工作写进 `finally`
:::
