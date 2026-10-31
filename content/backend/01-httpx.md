---
id: httpx
part: Web 服务
title: HTTP 和 HTTPX
lede: Agent 的每一步几乎都在调用接口。这一章用 HTTPX 发请求，处理超时、错误和重试，顺手把 OkHttp 的经验搬过来。
source: HTTPX 快速入门 | https://www.python-httpx.org/quickstart/ ; 客户端 | https://www.python-httpx.org/advanced/clients/ ; 超时 | https://www.python-httpx.org/advanced/timeouts/ ; 异步支持 | https://www.python-httpx.org/async/ ; HTTPX2 | https://github.com/pydantic/httpx2
versions: HTTPX 0.28 · HTTPX2 2.16 · OkHttp 5.5
seo_title: Python HTTPX 教程：发请求、超时、重试和异步并发
seo_description: 用 HTTPX 调用 HTTP 接口：GET 和 POST、Client 复用连接、超时设置、错误处理、重试、异步并发和测试，并和 Java HttpClient、OkHttp 对比。
---

## 发请求 {#request}

HTTPX 是 Python 常用的 HTTP 客户端，同时支持同步和异步。`requests` 也很流行，但它只有同步接口，在 `async def` 里用会卡住事件循环。

```bash
pip install httpx
```

本章的示例用 `MockTransport` 代替真实网络，存成文件就能运行。真实项目里去掉 `transport` 参数，请求就会发到网络上。

:::compare 发送 GET 请求
```python
§ import httpx
§ def handler(request: httpx.Request) -> httpx.Response:
§     return httpx.Response(200, json={"name": "Ada", "page": request.url.params["page"]})
§ _get = httpx.get
§ httpx.get = lambda url, params: httpx.Client(transport=httpx.MockTransport(handler)).get(url, params=params)
import httpx

response = httpx.get(
    "https://api.example.com/users/1",
    params={"page": 2},
)

response.status_code  # => 200
response.json()  # => {'name': 'Ada', 'page': '2'}
```
```java no-run
§ void run() throws Exception {
var client = HttpClient.newHttpClient();
var request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com/users/1?page=2"))
    .build();

var response = client.send(request, BodyHandlers.ofString());
System.out.println(response.statusCode());
System.out.println(response.body());
§ }
```
```kotlin no-run
§ fun run() {
val client = OkHttpClient()
val request = Request.Builder()
    .url("https://api.example.com/users/1?page=2")
    .build()

client.newCall(request).execute().use { response ->
    println(response.code)
    println(response.body.string())
}
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 入口 | 模块函数或 `Client` | `HttpClient` | `OkHttpClient` |
| 查询参数 | `params` 字典，自动编码 | 自己拼进网址 | `HttpUrl.Builder` |
| 解析 JSON | `response.json()` | 用 Jackson | 用 Moshi 或 kotlinx.serialization |
| 关闭响应 | 自动 | 自动 | 要用 `use` 关闭 |

> 要点: `response.json()` 返回字典和列表。要拿到有类型的对象，再交给下一章的 Pydantic。
:::

POST 用 `json=` 发送 JSON，用 `data=` 发送表单，用 `headers=` 加请求头。

```python
§ import httpx
§ def handler(request: httpx.Request) -> httpx.Response:
§     return httpx.Response(201, json={"auth": request.headers["Authorization"], "body": request.content.decode()})
§ httpx.post = lambda url, json, headers: httpx.Client(transport=httpx.MockTransport(handler)).post(url, json=json, headers=headers)
response = httpx.post(
    "https://api.example.com/users",
    json={"name": "Ada"},
    headers={"Authorization": "Bearer token"},
)

response.json()["body"]  # => '{"name":"Ada"}'
```

## 复用连接 {#client}

`httpx.get` 每次都新建连接，调用一个服务多次时要改用 `Client`。它带连接池，还能统一设置基础地址、请求头和超时。

`Client` 相当于 `OkHttpClient`，一个服务创建一个，全局共用。在 FastAPI 里，把它放进 `lifespan` 创建和关闭。

:::compare 共用一个客户端
```python
§ import httpx
§ def handler(request: httpx.Request) -> httpx.Response:
§     return httpx.Response(200, json={"path": request.url.path, "ua": request.headers["User-Agent"]})
with httpx.Client(
    base_url="https://api.example.com/v1",
    headers={"User-Agent": "demo/1.0"},
§     transport=httpx.MockTransport(handler),
) as client:
    response = client.get("/users")

response.json()  # => {'path': '/v1/users', 'ua': 'demo/1.0'}
```
```java no-run
§ void run() {
var client = HttpClient.newBuilder()
    .connectTimeout(Duration.ofSeconds(5))
    .build();

// 基础地址和公共请求头要自己封装
var request = HttpRequest.newBuilder()
    .uri(URI.create(BASE_URL + "/users"))
    .header("User-Agent", "demo/1.0")
    .build();
§ }
§ static final String BASE_URL = "https://api.example.com/v1";
```
```kotlin no-run
val client = OkHttpClient.Builder()
    .addInterceptor { chain ->
        val request = chain.request().newBuilder()
            .header("User-Agent", "demo/1.0")
            .build()
        chain.proceed(request)
    }
    .build()
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 连接池 | `Client` 自带 | `HttpClient` 自带 | `OkHttpClient` 自带 |
| 公共请求头 | `headers` 参数 | 自己封装 | 拦截器 |
| 基础地址 | `base_url` | 自己封装 | Retrofit 的 `baseUrl` |
| 拦截请求 | `event_hooks` 或自定义 `transport` | 自己封装 | 拦截器 |
| 关闭 | `with` 或 `client.close()` | 进程结束时回收 | 进程结束时回收 |

> 要点: 不要在循环或每次请求里创建 `Client`，连接池会失去作用。
:::

## 超时 {#timeout}

HTTPX 默认的超时是 5 秒，这和 OkHttp 的默认 10 秒不同。调用大模型时，等待第一个字节就可能超过 5 秒，所以要主动调大读取超时。

:::compare 设置超时
```python
import httpx

timeout = httpx.Timeout(
    10.0,  # 其余阶段的默认值
    connect=5.0,
    read=60.0,
)
client = httpx.Client(timeout=timeout)
client.timeout.read  # => 60.0
```
```java no-run
§ void run() {
var client = HttpClient.newBuilder()
    .connectTimeout(Duration.ofSeconds(5))
    .build();

// 没有单独的读取超时，timeout 管到响应头返回
var request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com"))
    .timeout(Duration.ofSeconds(60))
    .build();
§ }
```
```kotlin no-run
val client = OkHttpClient.Builder()
    .connectTimeout(5, TimeUnit.SECONDS)
    .readTimeout(60, TimeUnit.SECONDS)
    .build()
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 默认值 | 各阶段 5 秒 | 不超时 | 各阶段 10 秒 |
| 读取超时的含义 | 两次收到数据的最长间隔 | 等响应头的总时间 | 两次收到数据的最长间隔 |
| 关闭超时 | `timeout=None` | 不设置 | 设成 `0` |

> 要点: 读取超时是两次收到数据的间隔，不是整个请求的总时长。流式响应可以很长，只要一直有数据就不会超时。
:::

## 错误处理 {#errors}

HTTPX 收到 4xx、5xx 不会抛异常，要调用 `raise_for_status()`。连接失败和超时则直接抛异常，它们的共同父类是 `httpx.HTTPError`。

:::compare 处理错误
```python
§ import httpx
§ client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
def get_user(client: httpx.Client, user_id: int) -> dict | None:
    try:
        response = client.get(f"https://api.example.com/users/{user_id}")
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise
    except httpx.TimeoutException:
        raise RuntimeError("服务超时")
    return response.json()

get_user(client, 9)  # => None
```
```java no-run
Map<String, Object> getUser(HttpClient client, HttpRequest request)
        throws Exception {
    try {
        var response = client.send(request, BodyHandlers.ofString());
        if (response.statusCode() == 404) {
            return null;
        }
        return mapper.readValue(response.body(), Map.class);
    } catch (HttpTimeoutException e) {
        throw new RuntimeException("服务超时", e);
    }
}
§ ObjectMapper mapper;
```
```kotlin no-run
fun getUser(client: OkHttpClient, request: Request): String? = try {
    client.newCall(request).execute().use { response ->
        when {
            response.code == 404 -> null
            !response.isSuccessful -> error("HTTP ${response.code}")
            else -> response.body.string()
        }
    }
} catch (e: java.net.SocketTimeoutException) {
    throw RuntimeException("服务超时", e)
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 4xx、5xx | 不抛，调用 `raise_for_status()` | 不抛，自己判断 | 不抛，看 `isSuccessful` |
| 超时 | `httpx.TimeoutException` | `HttpTimeoutException` | `SocketTimeoutException` |
| 连接失败 | `httpx.ConnectError` | `ConnectException` | `IOException` |

> 要点: 三种客户端都不把 4xx、5xx 当异常，这一点和 Retrofit 的挂起函数不同。忘记检查状态码时，错误页面会被当成正常内容解析。
:::

## 重试 {#retry}

`HTTPTransport(retries=3)` 只在连接失败时重试。429、5xx 这类响应要自己处理，通常用指数退避：每次多等一倍，再加一点随机抖动，避免大量客户端同时重试。

```python
§ import httpx
§ seen = []
§ def handler(request: httpx.Request) -> httpx.Response:
§     seen.append(1)
§     return httpx.Response(200 if len(seen) == 3 else 503, json={"ok": True})
§ client = httpx.Client(transport=httpx.MockTransport(handler))
§ import random
§ import time
import random
import time

RETRYABLE = {429, 500, 502, 503, 504}

def get_with_retry(client: httpx.Client, url: str, attempts: int = 4) -> httpx.Response:
    for attempt in range(attempts):
        response = client.get(url)
        if response.status_code not in RETRYABLE or attempt == attempts - 1:
            return response
        retry_after = response.headers.get("Retry-After")
        wait = float(retry_after) if retry_after else 2 ** attempt * 0.5
§         wait = 0
        time.sleep(wait + random.random() * 0.1)
    raise AssertionError("不会走到这里")

get_with_retry(client, "https://api.example.com").status_code  # => 200
```

:::warn 只重试幂等的请求
GET 可以放心重试。POST 可能已经在服务端生效了，只是响应丢了，重试会重复创建。如果服务支持幂等键，比如 `Idempotency-Key` 请求头，再重试 POST。
:::

## 异步并发 {#async}

在 `async def` 里用 `AsyncClient`，方法名和 `Client` 一样，多一个 `await`。配合 `TaskGroup` 或 `gather` 就能同时发多个请求。

:::compare 并发请求
```python
§ import httpx
§ def handler(request: httpx.Request) -> httpx.Response:
§     return httpx.Response(200, json={"id": int(request.url.path.rsplit("/", 1)[1])})
import asyncio

async def get_user(client: httpx.AsyncClient, user_id: int) -> dict:
    response = await client.get(f"/users/{user_id}")
    response.raise_for_status()
    return response.json()

async def main():
    async with httpx.AsyncClient(
        base_url="https://api.example.com",
§         transport=httpx.MockTransport(handler),
    ) as client:
        users = await asyncio.gather(*[get_user(client, i) for i in [1, 2]])
    print(users)  # => [{'id': 1}, {'id': 2}]

asyncio.run(main())
```
```java no-run
§ void run(HttpClient client, HttpRequest a, HttpRequest b) {
var first = client.sendAsync(a, BodyHandlers.ofString());
var second = client.sendAsync(b, BodyHandlers.ofString());

CompletableFuture.allOf(first, second).join();
System.out.println(first.join().body());
§ }
```
```kotlin no-run
suspend fun getUsers(api: UserApi): List<User> = coroutineScope {
    listOf(1, 2)
        .map { id -> async { api.getUser(id) } }
        .awaitAll()
}
§ class User
§ interface UserApi { suspend fun getUser(id: Int): User }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 客户端 | `AsyncClient` | `sendAsync` | Retrofit 的 `suspend fun` |
| 并发 | `gather` | `CompletableFuture.allOf` | `async` 加 `awaitAll` |
| 限制并发数 | `asyncio.Semaphore` | `Semaphore` | `Semaphore` |

> 要点: 同步的 `Client` 不能用在 `async def` 里，它会阻塞事件循环。
:::

## 测试 {#testing}

测试时不要访问真实网络。`MockTransport` 接收一个函数，由它决定每个请求返回什么，作用类似 `MockWebServer`，但不用启动服务。

```python
import httpx

def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/users/1":
        return httpx.Response(200, json={"name": "Ada"})
    return httpx.Response(404)

client = httpx.Client(
    transport=httpx.MockTransport(handler),
    base_url="https://api.example.com",
)

client.get("/users/1").json()  # => {'name': 'Ada'}
client.get("/users/2").status_code  # => 404
```

:::more HTTPX 和 HTTPX2
HTTPX 的 0.28 版发布于 2024 年底，之后 Pydantic 团队维护了一个新的分支 HTTPX2，用法基本相同。OpenAI 的 Python SDK 已经改用 HTTPX2，FastAPI 的 `TestClient` 也优先使用它。

自己的代码可以继续用 `httpx`，这是目前教程和项目里最常见的写法。只有要把客户端对象传给这些 SDK 时要注意，它们需要 `httpx2` 里的对象，`httpx.Client` 不能直接传进去。
:::

:::map HTTP 客户端写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `httpx.Client` | `HttpClient` | `OkHttpClient` | 全局共用一个 |
| `client.get(url, params=...)` | `HttpRequest.newBuilder()` | `Request.Builder()` | HTTPX 自动编码参数 |
| `response.raise_for_status()` | 判断 `statusCode()` | 判断 `isSuccessful` | 都不会自动抛异常 |
| `httpx.Timeout(read=60)` | `request.timeout()` | `readTimeout` | HTTPX 默认只有 5 秒 |
| `httpx.AsyncClient` | `sendAsync` | Retrofit `suspend fun` | 协程里用它 |
| `MockTransport` | `MockRestServiceServer` | `MockWebServer` | 不访问真实网络 |
:::

:::recap
- 调用同一个服务时用 `Client` 复用连接，全局共用一个
- `async def` 里用 `AsyncClient`，不要用 `requests` 和同步 `Client`
- 默认超时只有 5 秒，调用大模型要调大 `read`
- 4xx、5xx 不抛异常，记得调用 `raise_for_status()`
- 429 和 5xx 用指数退避重试，POST 只有幂等时才重试
- 测试用 `MockTransport`，不访问真实网络
:::
