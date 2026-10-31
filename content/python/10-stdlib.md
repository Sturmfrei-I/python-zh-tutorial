---
id: standard-library
part: 工程实践
title: 标准库巡礼
lede: 不逐个讲 API，只告诉你某个需求该找哪个模块，再看几个最常用的例子。
source: 标准库简介 | stdlib.html ; 标准库简介第二部分 | stdlib2.html
seo_title: Python 标准库教程：常用模块速览，对比 Java、Kotlin
seo_description: 按需求查 Python 标准库：pathlib、re、datetime、threading、asyncio、logging、decimal、unittest 等常用模块，并给出 Java、Kotlin 的对应写法。
---

## 模块地图 {#index}

Python 标准库覆盖面很广。遇到需求先查这张表，再去翻文档。

:::map 按需求找模块
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `pathlib`、`os`、`shutil` | `java.nio.file` | `kotlin.io.path` | 路径和文件操作 |
| `subprocess` | `ProcessBuilder` | `ProcessBuilder` | 运行外部命令 |
| `tempfile` | `Files.createTempFile` | `createTempFile` | 临时文件 |
| `glob` | `Files.newDirectoryStream` | `listDirectoryEntries` | 通配符查找文件 |
| `sys`、`argparse` | `args`、picocli | `args`、clikt | 命令行程序 |
| `re` | `java.util.regex` | `Regex` | 正则表达式 |
| `math`、`random`、`statistics` | `Math`、`Random` | `kotlin.math`、`Random` | 数学和随机数 |
| `datetime` | `java.time` | `java.time` | 日期时间 |
| `time` | `System.currentTimeMillis`、`Thread.sleep` | `System.currentTimeMillis`、`Thread.sleep` | 时间戳和休眠 |
| `collections` | `java.util` | `kotlin.collections` | `deque`、`Counter`、`defaultdict` |
| `itertools`、`functools` | Stream API | Sequence | `chain`、`groupby`、`lru_cache`、`partial` |
| `threading`、`concurrent.futures` | `java.util.concurrent` | `java.util.concurrent` | 多线程 |
| `multiprocessing` | 无 | 无 | 多进程，绕开 GIL |
| `asyncio` | `CompletableFuture` | 协程 | 异步 I/O |
| `logging` | SLF4J | SLF4J | 日志 |
| `decimal`、`fractions` | `BigDecimal` | `BigDecimal` | 精确计算 |
| `unittest`、`doctest` | JUnit | `kotlin.test` | 测试 |
| `urllib.request` | `java.net.http` | `java.net.http` | HTTP 请求，实际项目多用第三方库 `requests` |
| `sqlite3` | JDBC + 驱动 | JDBC + 驱动 | Python 内置了 SQLite |
| `hashlib`、`base64`、`uuid` | `MessageDigest`、`Base64`、`UUID` | `MessageDigest`、`Base64`、`UUID` | 摘要、编码和唯一 ID |
:::

## 文件和路径 {#paths}

路径操作首选 `pathlib`。`/` 运算符用来拼接路径，读起来很直观。

:::compare 路径操作
```python
from pathlib import Path

p = Path("src") / "app" / "main.py"
print(p)         # => src/app/main.py
print(p.name)    # => main.py
print(p.suffix)  # => .py
print(p.parent)  # => src/app
```
```java
var p = Path.of("src", "app", "main.py");
System.out.println(p);  // => src/app/main.py
System.out.println(p.getFileName());  // => main.py
System.out.println(p.getParent());    // => src/app
```
```kotlin
import kotlin.io.path.*

val p = Path("src") / "app" / "main.py"
println(p)            // => src/app/main.py
println(p.name)       // => main.py
println(p.extension)  // => py
println(p.parent)     // => src/app
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 路径类型 | `pathlib.Path` | `java.nio.file.Path` | `java.nio.file.Path` |
| 拼接 | `/` 运算符 | `Path.of` 或 `resolve` | `/` 运算符 |
| 文件名 | `p.name` | `p.getFileName()` | `p.name` |
| 扩展名 | `p.suffix`，含点 | 需要自己截取 | `p.extension`，不含点 |
| 父目录 | `p.parent` | `p.getParent()` | `p.parent` |

> 要点: `Path.cwd().glob("**/*.py")` 递归查找文件。`os.environ` 读环境变量，`shutil.copy` 复制文件。
:::

`os` 和 `shutil` 负责系统和文件操作。`glob` 用通配符查找文件。

```python
import glob
import os
import shutil
from pathlib import Path

Path("a.txt").write_text("hi")
shutil.copyfile("a.txt", "b.txt")  # 复制文件
shutil.move("b.txt", "c.txt")      # 移动文件

print(sorted(glob.glob("*.txt")))  # => ['a.txt', 'c.txt']
print(os.path.exists("c.txt"))     # => True
print(os.getcwd())                 # 当前工作目录
```

`os.chdir()` 切换目录，`os.environ` 读环境变量。运行外部命令用 `subprocess.run()`，比 `os.system()` 更安全，也能拿到输出。

:::warn 不要写 from os import *
这样写会用 `os.open()` 覆盖内置的 `open()`，两者用法完全不同，代码会莫名其妙地出错。
:::

## 命令行参数 {#argv}

`sys.argv` 是参数列表，第一项是脚本名，这和 Java 的 `args` 不同。需要选项解析时用 `argparse`，它会自动生成 `--help`。

```python
§ import sys
§ sys.argv = ["app", "Ann", "-n", "2"]
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("name")
parser.add_argument("-n", "--count", type=int, default=1)
args = parser.parse_args()

print(args.name, args.count)  # => Ann 2
```

向标准错误输出写 `print("出错", file=sys.stderr)`，退出程序写 `sys.exit(1)`，对应 `System.err` 和 `System.exit(1)`。

## 正则表达式 {#re}

正则写在原始字符串 `r"..."` 里，不用双写反斜杠。

:::compare 正则匹配和替换
```python
import re

text = "2026-10-30"
m = re.match(r"(\d+)-(\d+)", text)
print(m.group(1))                # => 2026
print(re.findall(r"\d+", text))  # => ['2026', '10', '30']
print(re.sub(r"-", "/", text))   # => 2026/10/30
```
```java
var text = "2026-10-30";
var m = Pattern.compile("(\\d+)-(\\d+)")
    .matcher(text);
m.find();
System.out.println(m.group(1));  // => 2026
var r = text.replaceAll("-", "/");
System.out.println(r);  // => 2026/10/30
```
```kotlin
val text = "2026-10-30"
val m = Regex("""(\d+)-(\d+)""").find(text)
println(m?.groupValues?.get(1))  // => 2026
val all = Regex("""\d+""").findAll(text)
println(all.map { it.value }.toList())  // => [2026, 10, 30]
println(text.replace("-", "/"))  // => 2026/10/30
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 正则写法 | `r"\d+"` | `"\\d+"`，要双写反斜杠 | `"""\d+"""` |
| 匹配开头 | `re.match` | `matcher.lookingAt()` | `regex.matchAt(text, 0)` |
| 搜索任意位置 | `re.search` | `matcher.find()` | `regex.find` |
| 查找全部 | `re.findall` | `matcher.results()` | `regex.findAll` |
| 替换 | `re.sub` | `replaceAll` | `regex.replace` |
| 分组语法 | `(\d+)` | = | = |

> 要点: `re.match` 只从开头匹配，`re.fullmatch` 要求整串匹配。简单替换直接用 `str.replace`。
:::

## 数学和随机数 {#math}

```python
import math
import random
import statistics

data = [1, 2, 3, 6]
print(math.ceil(2.1))           # => 3
print(math.log(1024, 2))        # => 10.0
print(statistics.mean(data))    # => 3
print(statistics.median(data))  # => 2.5
print(statistics.variance(data))

print(random.choice(["a", "b"]))     # 随机取一个
print(random.sample(range(100), 3))  # 不重复地取 3 个
print(random.random())               # 0 到 1 之间的浮点数
print(random.randrange(6))           # 0 到 5 之间的整数
```

`random.shuffle` 原地打乱列表。涉及安全的随机数要用 `secrets` 模块，相当于 `SecureRandom`。复杂的数值计算用第三方库 NumPy 和 SciPy。


## 访问网络 {#http}

标准库的 `urllib.request` 能发 HTTP 请求，`smtplib` 能发邮件。

:::compare 发起 HTTP 请求
```python
from urllib.request import urlopen

url = "https://example.com"
with urlopen(url) as resp:
    print(resp.status)   # => 200
    body = resp.read().decode("utf-8")

print("Example" in body)  # => True
```
```java
§ import java.net.http.*;
var client = HttpClient.newHttpClient();
var req = HttpRequest
    .newBuilder(URI.create("https://example.com"))
    .build();
var resp = client.send(req,
    HttpResponse.BodyHandlers.ofString());
System.out.println(resp.statusCode());  // => 200
```
```kotlin
import java.net.URI

val body = URI("https://example.com")
    .toURL().readText()

println("Example" in body)  // => true
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 标准库 | `urllib.request` | `java.net.http.HttpClient` | `URL.readText()` |
| 响应内容 | 字节，要自己 `decode` | 由 `BodyHandler` 决定 | 字符串 |
| 常用第三方库 | `requests`、`httpx` | OkHttp | Ktor Client |

> 要点: 实际项目基本都用 `requests`，一行就能写完：`requests.get(url).json()`。
:::

## 日期和时间 {#datetime}

`date.today()` 取当天日期，`datetime.now()` 取当前时间。

:::compare 日期运算
```python
from datetime import date, timedelta

d = date(2026, 10, 30)
print(d + timedelta(days=7))  # => 2026-11-06
print(d.strftime("%Y/%m/%d")) # => 2026/10/30

days = (date(2027, 1, 1) - d).days
print(days)                   # => 63
```
```java
§ import java.time.*;
§ import java.time.format.*;
§ import java.time.temporal.*;
var d = LocalDate.of(2026, 10, 30);
System.out.println(d.plusDays(7));  // => 2026-11-06
var fmt = DateTimeFormatter
    .ofPattern("yyyy/MM/dd");
System.out.println(d.format(fmt));  // => 2026/10/30

var end = LocalDate.of(2027, 1, 1);
var days = ChronoUnit.DAYS.between(d, end);
System.out.println(days);           // => 63
```
```kotlin
§ import java.time.LocalDate
§ import java.time.format.DateTimeFormatter
§ import java.time.temporal.ChronoUnit
val d = LocalDate.of(2026, 10, 30)
println(d.plusDays(7))  // => 2026-11-06
val fmt = DateTimeFormatter
    .ofPattern("yyyy/MM/dd")
println(d.format(fmt))  // => 2026/10/30

val end = LocalDate.of(2027, 1, 1)
println(ChronoUnit.DAYS.between(d, end))  // => 63
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 日期类型 | `date`、`datetime` | `LocalDate`、`LocalDateTime` | `LocalDate`、`LocalDateTime` |
| 加减天数 | `d + timedelta(days=7)` | `d.plusDays(7)` | `d.plusDays(7)` |
| 格式化 | `d.strftime("%Y/%m/%d")` | `DateTimeFormatter` | `DateTimeFormatter` |
| 日期差 | `(a - b).days` | `ChronoUnit.DAYS.between` | `ChronoUnit.DAYS.between` |

> 要点: `datetime.now()` 默认不带时区，服务端代码应该写 `datetime.now(timezone.utc)`。
:::

## 并发 {#threads}

`threading.Thread` 是最基础的方式，`start` 启动线程，`join` 等待线程结束。

:::compare 创建线程
```python
import threading

results = []
lock = threading.Lock()

def work(n):
    with lock:
        results.append(n * n)

threads = [
    threading.Thread(target=work, args=(i,))
    for i in range(3)
]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(sorted(results))  # => [0, 1, 4]
```
```java
var results = new ConcurrentLinkedQueue<Integer>();
var threads = new ArrayList<Thread>();

for (int i = 0; i < 3; i++) {
    int n = i;
    var t = new Thread(() -> results.add(n * n));
    t.start();
    threads.add(t);
}
for (var t : threads) {
    t.join();
}

var sorted = new TreeSet<>(results);
System.out.println(sorted);  // => [0, 1, 4]
```
```kotlin
import java.util.concurrent.ConcurrentLinkedQueue
import kotlin.concurrent.thread

val results = ConcurrentLinkedQueue<Int>()

val threads = (0 until 3).map { n ->
    thread { results.add(n * n) }
}
threads.forEach { it.join() }

println(results.sorted())  // => [0, 1, 4]
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 创建 | `Thread(target=f, args=(1,))` | `new Thread(runnable)` | `thread { }` |
| 启动 | 调用 `start()` | 调用 `start()` | 创建时自动启动 |
| 加锁 | `with lock:` | `synchronized` | `synchronized` |
| 线程安全队列 | `queue.Queue` | `BlockingQueue` | `BlockingQueue` |
| 等待结束 | `t.join()` | = | = |
| 同步工具 | `Event`、`Semaphore`、`Condition` | 有对应类 | 有对应类 |

> 要点: 多个线程协作时，优先让它们通过 `queue.Queue` 传递任务，这比到处加锁更不容易出错。
:::

批量执行任务时用线程池，这是日常最常用的写法。

:::compare 线程池
```python
from concurrent.futures import ThreadPoolExecutor

def square(n):
    return n * n

with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(square, [1, 2, 3]))

print(results)  # => [1, 4, 9]
```
```java
var pool = Executors.newFixedThreadPool(4);
var tasks = new ArrayList<Future<Integer>>();
for (int n : List.of(1, 2, 3)) {
    tasks.add(pool.submit(() -> n * n));
}
for (var task : tasks) {
    System.out.println(task.get());
}
pool.shutdown();
```
```kotlin no-run
// 使用 kotlinx.coroutines
val results = runBlocking {
    listOf(1, 2, 3).map { n ->
        async(Dispatchers.Default) { n * n }
    }.awaitAll()
}
println(results)  // => [1, 4, 9]
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 线程池 | `ThreadPoolExecutor` | `Executors.newFixedThreadPool` | 协程，也能用 Java 线程池 |
| 关闭 | `with` 结束时自动关闭 | 调用 `shutdown()` | 由 `runBlocking` 管理 |
| CPU 密集任务 | 受 GIL 限制，要用多进程 | 多核并行 | 多核并行 |
| 结果顺序 | `pool.map` 按输入顺序 | 按 `Future` 列表顺序 | `awaitAll` 按输入顺序 |

> 要点: `with` 结束时会等待所有任务完成，不用手动收尾。
:::

:::warn GIL 限制
CPython 3.12 有全局解释器锁（GIL），同一时刻只有一个线程执行 Python 字节码。线程适合网络请求这样的 I/O 密集任务。CPU 密集任务开线程不会变快，要用 `ProcessPoolExecutor` 开多进程。这是和 JVM 差别最大的地方之一。
:::

## 异步编程 {#async}

`asyncio` 用单线程事件循环处理大量 I/O。`async def` 定义协程，`await` 等待结果并让出控制权。官方教程没有讲它，但现代 Python 的网络框架大多基于它。这里只看最基本的用法，详细内容见「异步编程和异步生成器」一章。

:::compare 并发执行多个任务
```python
import asyncio

async def fetch(n):
    await asyncio.sleep(0.01)
    return n * n

async def main():
    results = await asyncio.gather(
        fetch(1), fetch(2), fetch(3))
    print(results)  # => [1, 4, 9]

asyncio.run(main())
```
```java
static CompletableFuture<Integer> fetch(int n) {
    return CompletableFuture.supplyAsync(
        () -> n * n);
}

var tasks = List.of(fetch(1), fetch(2), fetch(3));
var results = tasks.stream()
    .map(CompletableFuture::join)
    .toList();
System.out.println(results);  // => [1, 4, 9]
```
```kotlin no-run
// 使用 kotlinx.coroutines
suspend fun fetch(n: Int): Int {
    delay(10)
    return n * n
}

fun main() = runBlocking {
    val results = listOf(1, 2, 3)
        .map { async { fetch(it) } }
        .awaitAll()
    println(results)  // => [1, 4, 9]
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明 | `async def` | 返回 `CompletableFuture` | `suspend fun` |
| 等待结果 | `await` | `join()` 或回调 | 直接调用 |
| 并发执行 | `asyncio.gather` | `CompletableFuture.allOf` | `async` + `awaitAll` |
| 程序入口 | `asyncio.run(main())` | 不需要 | `runBlocking` |
| 运行方式 | 单线程事件循环 | 线程池 | 协程调度器 |
| 适合场景 | 大量并发 I/O | = | = |

> 要点: 协程里不能调用会阻塞的函数，比如 `time.sleep` 和 `requests.get`，否则整个事件循环都会停住。要用 `asyncio.sleep` 和 `httpx` 这样的异步版本。
:::

## 日志 {#logging}

:::compare 记录日志
```python
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

log.info("端口 %d", 8080)
log.warning("磁盘快满了")
```
```java no-run
private static final Logger log =
    LoggerFactory.getLogger(App.class);

log.info("端口 {}", 8080);
log.warn("磁盘快满了");
```
```kotlin no-run
private val log =
    LoggerFactory.getLogger("App")

log.info("端口 {}", 8080)
log.warn("磁盘快满了")
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 来源 | 标准库 `logging` | 第三方 SLF4J | 第三方 SLF4J |
| 获取日志器 | `getLogger(__name__)` | `getLogger(App.class)` | `getLogger("App")` |
| 占位符 | `%d`、`%s` | `{}` | `{}` |
| 警告级别 | `log.warning` | `log.warn` | `log.warn` |
| 延迟格式化 | 消息真正输出时才格式化 | = | = |

> 要点: 不要在日志里用 f-string，否则每次调用都会格式化。默认级别是 `WARNING`，输出到标准错误。
:::

日志级别从低到高是 `DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`，分别对应 `log.debug()` 到 `log.critical()`。配置既可以写在代码里，也可以从配置文件加载。

## 精确小数 {#decimal}

金额计算不能用 `float`，要用 `Decimal`，对应 `BigDecimal`。构造时要传字符串。

:::compare 精确计算
```python
from decimal import Decimal, ROUND_HALF_UP

a = Decimal("0.1")
b = Decimal("0.2")
print(a + b)  # => 0.3

cents = Decimal("0.01")
price = Decimal("2.675")
print(price.quantize(cents, ROUND_HALF_UP))  # => 2.68
```
```java
var a = new BigDecimal("0.1");
var b = new BigDecimal("0.2");
System.out.println(a.add(b));  // => 0.3

var price = new BigDecimal("2.675")
    .setScale(2, RoundingMode.HALF_UP);
System.out.println(price);     // => 2.68
```
```kotlin
import java.math.RoundingMode

val a = "0.1".toBigDecimal()
val b = "0.2".toBigDecimal()
println(a + b)  // => 0.3

val price = "2.675".toBigDecimal()
    .setScale(2, RoundingMode.HALF_UP)
println(price)  // => 2.68
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 类型 | `Decimal` | `BigDecimal` | `BigDecimal` |
| 运算写法 | 普通运算符 | `add`、`multiply` 等方法 | 普通运算符 |
| 舍入 | `quantize(cents, ROUND_HALF_UP)` | `setScale(2, HALF_UP)` | `setScale(2, HALF_UP)` |
| 全局精度 | `getcontext().prec = 36` | 每次传 `MathContext` | 每次传 `MathContext` |
| 构造方式 | 传字符串，避免浮点误差 | = | = |

> 要点: 金额计算不能用 `float`。构造时传浮点数会把误差一起带进来。
:::

## 测试 {#testing}

标准库自带 `unittest`，结构和 JUnit 一样。运行命令是 `python3 -m unittest`。

:::compare 单元测试
```python
import unittest

class MathTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)

    def test_zero(self):
        with self.assertRaises(ZeroDivisionError):
            1 / 0
§ 
§ import sys
§ loader = unittest.defaultTestLoader
§ runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=0)
§ print(runner.run(loader.loadTestsFromTestCase(MathTest)).wasSuccessful())  # => True
```
```java no-run
class MathTest {
    @Test
    void add() {
        assertEquals(2, 1 + 1);
    }

    @Test
    void zero() {
        assertThrows(ArithmeticException.class,
            () -> { int x = 1 / 0; });
    }
}
```
```kotlin no-run
class MathTest {
    @Test
    fun add() {
        assertEquals(2, 1 + 1)
    }

    @Test
    fun zero() {
        assertFailsWith<ArithmeticException> {
            1 / 0
        }
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 框架 | 标准库 `unittest` | 第三方 JUnit | `kotlin.test` |
| 测试标记 | 方法名以 `test` 开头 | `@Test` 注解 | `@Test` 注解 |
| 测试类 | 继承 `unittest.TestCase` | 普通类 | 普通类 |
| 断言相等 | `assertEqual(a, b)` | `assertEquals(a, b)` | `assertEquals(a, b)` |
| 断言异常 | `with assertRaises(E):` | `assertThrows(E.class, ...)` | `assertFailsWith<E> { }` |

> 要点: 实际项目大多用第三方的 `pytest`。测试写成普通函数，直接用 `assert`，比 `unittest` 简洁很多。
:::

`doctest` 能运行文档字符串里的交互式示例，适合保证文档不过时。

```python
def double(n):
    """返回 n 的两倍。

    >>> double(4)
    8
    """
    return n * 2

import doctest
print(doctest.testmod().failed)  # => 0
```

## 其余模块 {#rest}

下面这些用到时再查，知道有就行。

- 压缩归档：`zlib`、`gzip`、`bz2`、`lzma`、`zipfile`、`tarfile`
- 性能测量：`timeit` 测小段代码，`cProfile`、`profile` 和 `pstats` 找程序热点
- 高效数据结构：`heapq` 对应 `PriorityQueue`，`bisect` 对应 `Collections.binarySearch`，`array` 对应基本类型数组
- 二进制数据：`struct` 的 `pack` 和 `unpack`，对应 `ByteBuffer`
- 内存管理：CPython 用引用计数加循环垃圾回收，`gc` 模块可以手动触发，`weakref` 对应 `WeakReference`
- 调整显示：`textwrap` 折行，`pprint` 美化输出数据结构，`reprlib` 缩略显示大对象
- 文本模板：`string.Template` 的 `substitute` 和 `safe_substitute`，适合让用户自定义格式
- 国际化：`locale`、`gettext`、`codecs`
- 数据格式：`csv`、`xml.etree.ElementTree`、`xml.dom`、`xml.sax`
- 邮件和远程调用：`email`、`poplib`、`xmlrpc.client`、`xmlrpc.server`

:::recap
- 路径用 `pathlib`，日期用 `datetime`，精确小数用 `decimal`
- 正则写在 `r"..."` 里，`match` 只匹配开头，`search` 匹配任意位置
- 线程用 `threading`，线程池用 `concurrent.futures`，CPU 密集任务要用多进程，因为有 GIL
- 大量并发 I/O 用 `asyncio`，协程里不能调用阻塞函数
- 日志用 `logging`，占位符交给日志库格式化
- 测试可以用 `unittest`，实际项目多用 `pytest`
:::
