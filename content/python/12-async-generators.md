---
id: async-generators
part: 工程实践
title: 异步编程和异步生成器
lede: 一个线程同时等几十个网络请求，靠的就是协程。这一章讲清 async、await 和异步生成器，它们和 Kotlin 的 suspend、Flow 几乎一一对应。
source: 协程与任务 | https://docs.python.org/zh-cn/3.12/library/asyncio-task.html ; 异步生成器函数 | https://docs.python.org/zh-cn/3.12/reference/expressions.html#asynchronous-generator-functions ; PEP 525 异步生成器 | https://peps.python.org/pep-0525/ ; Kotlin Flow | https://kotlinlang.org/docs/flow.html ; Reactor 参考文档 | https://projectreactor.io/docs/core/release/reference/
versions: Python 3.12 · Kotlin 协程 1.11 · Reactor 3
seo_title: Python 异步生成器教程：asyncio、async for，对比 Flow
seo_description: 讲解 Python 的 async、await、TaskGroup、超时、异步生成器、async for、aclosing 和 asyncio.Queue，并和 Kotlin 协程、Flow、Java 虚拟线程对比。
---

## 协程 {#coroutine}

`async def` 定义协程函数，调用它只会得到一个协程对象，函数体不会运行。协程要交给事件循环才会执行，`asyncio.run` 负责启动事件循环，`await` 负责等待结果。

等待期间事件循环可以运行别的协程，所以一个线程能同时处理很多网络请求。

:::compare 定义和调用协程
```python
import asyncio

async def fetch(name: str) -> str:
    await asyncio.sleep(0.01)
    return f"{name} 完成"

async def main():
    result = await fetch("任务")
    print(result)  # => 任务 完成

asyncio.run(main())
```
```java no-run
String fetch(String name) throws InterruptedException {
    Thread.sleep(10);  // 在虚拟线程上阻塞很便宜
    return name + " 完成";
}

void main() throws Exception {
    try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
        var result = pool.submit(() -> fetch("任务"));
        System.out.println(result.get());
    }
}
```
```kotlin no-run
suspend fun fetch(name: String): String {
    delay(10)
    return "$name 完成"
}

fun main() = runBlocking {
    println(fetch("任务"))
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明 | `async def` | 普通方法 | `suspend fun` |
| 等待 | 必须写 `await` | 直接调用 | 直接调用 |
| 入口 | `asyncio.run()` | 线程池 | `runBlocking` |
| 调用但不等待 | 得到协程对象，不运行 | 方法立即运行 | 没有这种情况，调用时自动等待 |

> 要点: 最常见的错误是漏写 `await`。函数不会运行，只有一条 `was never awaited` 警告。
:::

:::warn 协程里不能阻塞
事件循环只有一个线程，协程里调用 `time.sleep` 或 `requests.get` 会卡住所有协程。这和 Android 主线程上不能做耗时操作是一回事。阻塞函数要用 `await asyncio.to_thread(函数, 参数)` 放到线程池运行。
:::

## 同时运行多个任务 {#taskgroup}

依次 `await` 是串行的。要并发运行，用 `asyncio.TaskGroup` 创建任务，离开 `async with` 时所有任务都已结束。这就是结构化并发，和 Kotlin 的 `coroutineScope` 是同一个思路。

:::compare 并发运行任务
```python
import asyncio

async def fetch(name: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return name

async def main():
    async with asyncio.TaskGroup() as group:
        a = group.create_task(fetch("a", 0.02))
        b = group.create_task(fetch("b", 0.01))
    print(a.result(), b.result())  # => a b

asyncio.run(main())
```
```java no-run
void main() throws Exception {
    try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
        Future<String> a = pool.submit(() -> fetch("a", 20));
        Future<String> b = pool.submit(() -> fetch("b", 10));
        System.out.println(a.get() + " " + b.get());
    }
}
§ String fetch(String name, long ms) throws InterruptedException {
§     Thread.sleep(ms);
§     return name;
§ }
```
```kotlin no-run
suspend fun fetch(name: String, ms: Long): String {
    delay(ms)
    return name
}

fun main() = runBlocking {
    coroutineScope {
        val a = async { fetch("a", 20) }
        val b = async { fetch("b", 10) }
        println("${a.await()} ${b.await()}")
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 作用域 | `async with TaskGroup()` | `try` 里的线程池 | `coroutineScope` |
| 启动任务 | `create_task` | `submit` | `async` |
| 取结果 | `task.result()` | `future.get()` | `await()` |
| 一个任务失败 | 取消其他任务，抛 `ExceptionGroup` | 其他任务继续 | 取消其他任务，抛出异常 |

> 要点: 只想收集结果时也可以用 `asyncio.gather`。新代码优先用 `TaskGroup`，失败时不会留下还在运行的任务。
:::

`TaskGroup` 里任务失败时抛的是 `ExceptionGroup`，要用 `except*` 捕获。

```python
import asyncio

async def boom():
    raise ValueError("出错了")

async def main():
    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(boom())
    except* ValueError as errors:
        print(errors.exceptions[0])

asyncio.run(main())
```
```output
出错了
```

超时用 `asyncio.timeout`，到时间后里面的协程被取消，外面收到 `TimeoutError`。

```python
import asyncio

async def main():
    try:
        async with asyncio.timeout(0.01):
            await asyncio.sleep(1)
    except TimeoutError:
        print("超时")

asyncio.run(main())
```
```output
超时
```

## 异步生成器 {#generator}

普通生成器用 `yield` 一次产出一个值。`async def` 里写 `yield` 就是异步生成器，产出两个值之间可以 `await`。消费方用 `async for` 读取。

大模型流式回答就是这个场景：一个片段到了才产出一个片段，等待期间不占线程。

:::compare 定义和消费数据流
```python
import asyncio

async def count(n: int):
    for i in range(n):
        await asyncio.sleep(0.01)
        yield i

async def main():
    async for value in count(3):
        print(value)

asyncio.run(main())
```
```java no-run
Flux<Integer> count(int n) {
    return Flux.range(0, n)
        .delayElements(Duration.ofMillis(10));
}

void main() {
    count(3).doOnNext(System.out::println).blockLast();
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
    count(3).collect { println(it) }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 类型 | `AsyncGenerator` | `Flux` | `Flow` |
| 产出 | `yield` | 操作符或 `sink.next` | `emit` |
| 消费 | `async for` | `subscribe` | `collect` |
| 惰性 | 消费时才运行 | = | = |
| 重复消费 | 不能，读完就空了 | 可以，每次重新运行 | 可以，每次重新运行 |

> 要点: 异步生成器是一次性的，这是和 `Flow` 最大的不同。要读第二遍，就再调用一次函数。
:::

函数里 `yield` 暂停时，消费方取走一个值才会继续，所以不需要额外处理背压，生成速度自然跟着消费速度走。

## 转换数据流 {#transform}

Python 没有 `map`、`filter` 这样的异步操作符，写法是再包一层异步生成器，或者用异步推导式。

:::compare 过滤和转换
```python
import asyncio

async def count(n: int):
    for i in range(n):
        yield i

async def even_squares(n: int):
    async for value in count(n):
        if value % 2 == 0:
            yield value * value

async def main():
    print([v async for v in even_squares(5)])  # => [0, 4, 16]

asyncio.run(main())
```
```java no-run
void main() {
    var result = Flux.range(0, 5)
        .filter(value -> value % 2 == 0)
        .map(value -> value * value)
        .collectList()
        .block();
    System.out.println(result);
}
```
```kotlin no-run
fun main() = runBlocking {
    val result = (0 until 5).asFlow()
        .filter { it % 2 == 0 }
        .map { it * it }
        .toList()
    println(result)
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 转换 | 再写一个异步生成器 | `map` | `map` |
| 过滤 | 生成器里写 `if` | `filter` | `filter` |
| 收集成列表 | `[v async for v in s]` | `collectList` | `toList` |

> 要点: 写法比链式操作符长，但就是普通的 `for` 和 `if`，调试起来更直接。
:::

## 提前结束 {#close}

消费方用 `break` 提前退出时，异步生成器不会马上结束。它的 `finally` 要等事件循环稍后清理时才运行。如果里面占着网络连接，连接就多占了一段时间。

```python
import asyncio

async def tokens():
    try:
        for word in ["你", "好", "吗"]:
            yield word
    finally:
        print("释放连接")

async def main():
    async for word in tokens():
        print(word)
        break
    print("后续代码")

asyncio.run(main())
```
```output
你
后续代码
释放连接
```

要让它立刻清理，用 `contextlib.aclosing` 包起来。离开 `async with` 时生成器马上关闭，`finally` 已经运行完。

```python
import asyncio
from contextlib import aclosing

async def tokens():
    try:
        for word in ["你", "好", "吗"]:
            yield word
    finally:
        print("释放连接")

async def main():
    async with aclosing(tokens()) as stream:
        async for word in stream:
            print(word)
            break
    print("后续代码")

asyncio.run(main())
```
```output
你
释放连接
后续代码
```

Kotlin 的 `Flow` 没有这个问题，`take(1)` 结束时 `finally` 立刻运行。

## 用队列连接生产者和消费者 {#queue}

几个流要合并成一个，或者生产和消费要分开运行时，用 `asyncio.Queue`。它相当于 Kotlin 的 `Channel`。

:::compare 合并两个来源
```python
import asyncio

async def produce(name: str, queue: asyncio.Queue):
    for i in range(2):
        await queue.put(f"{name}{i}")

async def main():
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=10)
    async with asyncio.TaskGroup() as group:
        group.create_task(produce("a", queue))
        group.create_task(produce("b", queue))
    items = [queue.get_nowait() for _ in range(queue.qsize())]
    print(sorted(items))  # => ['a0', 'a1', 'b0', 'b1']

asyncio.run(main())
```
```java no-run
void main() throws Exception {
    var queue = new ArrayBlockingQueue<String>(10);
    try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
        pool.submit(() -> produce("a", queue));
        pool.submit(() -> produce("b", queue));
    }
    System.out.println(new TreeSet<>(queue));
}
§ Void produce(String name, BlockingQueue<String> queue) throws Exception {
§     queue.put(name);
§     return null;
§ }
```
```kotlin no-run
fun main() = runBlocking {
    val channel = Channel<String>(capacity = 10)
    coroutineScope {
        launch { produce("a", channel) }
        launch { produce("b", channel) }
    }
    channel.close()
    println(channel.toList().sorted())
}
§ suspend fun produce(name: String, channel: Channel<String>) {
§     channel.send(name)
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 类型 | `asyncio.Queue` | `ArrayBlockingQueue` | `Channel` |
| 放入 | `await queue.put()` | `queue.put()` | `channel.send()` |
| 取出 | `await queue.get()` | `queue.take()` | `channel.receive()` |
| 满了以后 | 挂起等待 | 阻塞等待 | 挂起等待 |

> 要点: 给队列设置 `maxsize`，否则生产者比消费者快时内存会一直涨。
:::

:::map 异步写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `async def` | 虚拟线程上的普通方法 | `suspend fun` | Python 必须写 `await` |
| `asyncio.run()` | `newVirtualThreadPerTaskExecutor()` | `runBlocking` | 程序入口 |
| `TaskGroup` | `try` 里的线程池 | `coroutineScope` | 结构化并发 |
| `asyncio.timeout()` | `future.get(超时)` | `withTimeout` | 超时后取消任务 |
| `asyncio.to_thread()` | 不需要 | `withContext(Dispatchers.IO)` | 把阻塞代码移走 |
| 异步生成器 | `Flux` | `Flow` | 只有 Python 的不能重复消费 |
| `aclosing()` | 自动清理 | 自动清理 | 提前退出时才需要 |
| `asyncio.Queue` | `ArrayBlockingQueue` | `Channel` | 记得限制容量 |
:::

:::recap
- `async def` 定义协程，调用后要 `await` 或交给事件循环，否则不会运行
- 协程里不能阻塞，阻塞函数用 `asyncio.to_thread`
- 并发用 `TaskGroup`，超时用 `asyncio.timeout`
- `async def` 里写 `yield` 就是异步生成器，用 `async for` 消费，只能读一遍
- 转换数据流时再包一层生成器，提前退出时用 `aclosing` 立刻清理
- 合并多个来源用 `asyncio.Queue`，并设置容量上限
:::
