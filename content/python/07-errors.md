---
id: exceptions
part: 对象、异常与文件
title: 错误与异常
lede: 结构和 try/catch 一样，多了一个 else 分支。Python 没有受检异常，鼓励先做再处理错误。
source: 错误和异常 | errors.html
seo_title: Python 异常处理：try、except 和 with，对比 Java
seo_description: 讲解 Python 的 try except else finally、异常链、自定义异常和 with 语句，并对比 Java 的受检异常和 try-with-resources。
---

## 捕获异常 {#try}

`catch` 写成 `except`。`else` 分支只在没有异常时执行，`finally` 无论如何都会执行。

:::compare try 的完整结构
```python
def parse(text):
    try:
        value = int(text)
    except ValueError as e:
        print("无效:", e)
        return None
    else:
        print("成功")     # => 成功
        return value
    finally:
        print("清理")     # => 清理

print(parse("12"))        # => 12
```
```java
static Integer parse(String text) {
    try {
        var value = Integer.parseInt(text);
        System.out.println("成功");  // => 成功
        return value;
    } catch (NumberFormatException e) {
        System.out.println("无效: " + e);
        return null;
    } finally {
        System.out.println("清理");  // => 清理
    }
}
System.out.println(parse("12"));  // => 12
```
```kotlin
fun parse(text: String): Int? = try {
    val value = text.toInt()
    println("成功")      // => 成功
    value
} catch (e: NumberFormatException) {
    println("无效: $e")
    null
} finally {
    println("清理")      // => 清理
}
println(parse("12"))     // => 12
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 捕获 | `except` | `catch` | `catch` |
| 无异常时执行 | `else` 分支 | 写在 `try` 块末尾 | 写在 `try` 块末尾 |
| 能否当值用 | 不能，是语句 | 不能，是语句 | 可以，是表达式 |
| 同时捕获多种 | `except (A, B) as e` | `catch (A \| B e)` | 写多个 `catch` |
| `finally` | 总会执行 | = | = |

> 要点: `else` 让 `try` 块只包含可能出错的那一行。不要写裸的 `except:`，它连 `Ctrl-C` 都会吞掉。
:::

多个 `except` 按顺序匹配，第一个命中的分支生效，所以子类要写在父类前面。`e.args` 保存构造异常时传入的参数。

:::more finally 的细节
`finally` 在 `return`、`break`、`continue` 真正生效之前执行。如果 `finally` 自己也写了 `return`，它的返回值会覆盖 `try` 的返回值，异常也会被吞掉，所以不要在 `finally` 里写 `return`。
:::

## 没有受检异常 {#unchecked}

Python 和 Kotlin 一样，所有异常都是非受检的，函数签名里没有 `throws`。社区习惯 EAFP 风格（先做了再说），用捕获异常代替事先检查。

:::compare 先做再处理
```python
config = {"port": 8080}

try:
    host = config["host"]
except KeyError:
    host = "localhost"

print(host)  # => localhost
```
```java
var config = Map.of("port", "8080");

var host = config.containsKey("host")
    ? config.get("host")
    : "localhost";

System.out.println(host);  // => localhost
```
```kotlin
val config = mapOf("port" to "8080")

val host = config["host"] ?: "localhost"

println(host)  // => localhost
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 习惯风格 | 先做再处理（EAFP） | 先检查再做（LBYL） | 用可空类型处理 |
| 受检异常 | 没有 | 有，要写 `throws` | = |
| 取默认值 | `config.get("host", "x")` | `getOrDefault` | `config["host"] ?: "x"` |

> 要点: 这个例子用 `config.get` 更简洁。处理多步操作时 EAFP 的优势才明显，比如打开文件前不用先判断文件是否存在。
:::

:::map 常见异常对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `BaseException` | `Throwable` | `Throwable` | 根类 |
| `Exception` | `Exception` | `Exception` | 应用代码捕获到这一层为止 |
| `ValueError` | `IllegalArgumentException` | `IllegalArgumentException` | 值不合法 |
| `TypeError` | `ClassCastException` | `ClassCastException` | 类型不对 |
| `KeyError` | 无（`get` 返回 `null`） | `getValue` 抛 `NoSuchElementException` | 字典键不存在 |
| `IndexError` | `IndexOutOfBoundsException` | `IndexOutOfBoundsException` | 下标越界 |
| `ZeroDivisionError` | `ArithmeticException` | `ArithmeticException` | Python 里浮点数除以零也会抛这个异常 |
| `NameError` | 编译错误 | 编译错误 | 名字写错，运行到那一行才发现 |
| `ModuleNotFoundError` | `ClassNotFoundException` | `ClassNotFoundException` | `ImportError` 的子类 |
| `AttributeError` | `NullPointerException` | 无 | 常见于访问 `None` 的属性 |
| `FileNotFoundError` | `FileNotFoundException` | `FileNotFoundException` | |
| `NotImplementedError` | `UnsupportedOperationException` | `NotImplementedError` | 未实现的抽象方法 |
| `KeyboardInterrupt`、`SystemExit` | 无 | 无 | 继承 `BaseException`，所以 `except Exception` 拦不住 `Ctrl-C` 和 `sys.exit()` |
:::

## 抛出异常 {#raise}

`throw` 写成 `raise`，不用 `new`。包装底层异常时用 `from` 保留原因，相当于把 cause 传给构造函数。

:::compare 包装异常
```python
def load(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError as e:
        raise RuntimeError("加载失败") from e

try:
    load("/missing.txt")
except RuntimeError as e:
    print(e)                  # => 加载失败
    print(type(e.__cause__).__name__)  # => FileNotFoundError
```
```java
static String load(String path) {
    try {
        return Files.readString(Path.of(path));
    } catch (IOException e) {
        throw new RuntimeException("加载失败", e);
    }
}

try {
    load("/missing.txt");
} catch (RuntimeException e) {
    System.out.println(e.getMessage());  // => 加载失败
}
```
```kotlin
import java.io.File
import java.io.IOException

fun load(path: String): String = try {
    File(path).readText()
} catch (e: IOException) {
    throw RuntimeException("加载失败", e)
}

try {
    load("/missing.txt")
} catch (e: RuntimeException) {
    println(e.message)  // => 加载失败
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 抛出 | `raise` | `throw` | `throw` |
| 创建异常对象 | 不用 `new` | `new RuntimeException()` | 不用 `new` |
| 保留原因 | `raise X from e` | `new X(msg, e)` | `X(msg, e)` |
| 读取原因 | `e.__cause__` | `e.getCause()` | `e.cause` |
| 重新抛出 | 单独写 `raise` | `throw e` | `throw e` |

> 要点: 包装底层异常时要保留原因，否则排查问题时会丢掉最初的错误位置。
:::

不想显示原始异常时写 `raise X from None`。

`assert 条件, "消息"` 在条件为假时抛 `AssertionError`，用来检查不该发生的情况。`python3 -O` 运行时所有 `assert` 都会被跳过，所以不要用它校验用户输入。

## 自定义异常 {#custom}

继承 `Exception` 即可。类名通常以 `Error` 结尾。

:::compare 自定义异常类
```python
class OrderError(Exception):
    def __init__(self, order_id, message):
        super().__init__(message)
        self.order_id = order_id

try:
    raise OrderError(42, "库存不足")
except OrderError as e:
    print(e, e.order_id)  # => 库存不足 42
```
```java
class OrderException extends RuntimeException {
    final int orderId;

    OrderException(int orderId, String message) {
        super(message);
        this.orderId = orderId;
    }
}

try {
    throw new OrderException(42, "库存不足");
} catch (OrderException e) {
    System.out.println(
        e.getMessage() + " " + e.orderId);  // => 库存不足 42
}
```
```kotlin
class OrderException(
    val orderId: Int,
    message: String
) : RuntimeException(message)

try {
    throw OrderException(42, "库存不足")
} catch (e: OrderException) {
    println("${e.message} ${e.orderId}")  // => 库存不足 42
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 继承自 | `Exception` | `RuntimeException` 或 `Exception` | `RuntimeException` 或 `Exception` |
| 调用父类构造 | `super().__init__(msg)` | `super(msg)` | 类头的 `: RuntimeException(msg)` |
| 读取消息 | `str(e)` | `e.getMessage()` | `e.message` |
| 命名习惯 | 以 `Error` 结尾 | 以 `Exception` 结尾 | 以 `Exception` 结尾 |

> 要点: 给项目定义一个异常基类，其余异常都继承它，调用方就能一次捕获本项目的所有错误。
:::

## with 语句 {#with}

文件、锁、数据库连接这类资源要用 `with` 管理，代码块结束时自动释放，异常发生时也一样。

:::compare 自动释放资源
```python
with open("demo.txt", "w") as f:
    f.write("hello")

with open("demo.txt") as f:
    print(f.read())   # => hello
```
```java
var path = Path.of("demo.txt");
try (var out = Files.newBufferedWriter(path)) {
    out.write("hello");
}
try (var in = Files.newBufferedReader(path)) {
    System.out.println(in.readLine());  // => hello
}
§ Files.delete(path);
```
```kotlin
import java.io.File

val file = File("demo.txt")
file.bufferedWriter().use { it.write("hello") }
file.bufferedReader().use {
    println(it.readLine())  // => hello
}
§ file.delete()
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 语法 | `with ... as f:` | `try (var f = ...)` | `.use { }` |
| 依赖的约定 | `__enter__`、`__exit__` | `AutoCloseable` | `AutoCloseable` |
| 多个资源 | `with a, b:` | `try (a; b)` | 嵌套 `use` |
| 发生异常时 | 资源同样会释放 | = | = |

> 要点: 文件、锁、数据库连接这类资源都应该这样管理，不要手动调用 `close()`。
:::

:::more 自己写上下文管理器
`contextlib.contextmanager` 能把一个生成器函数变成上下文管理器，`yield` 之前是进入时的逻辑，之后是退出时的逻辑。

```python
from contextlib import contextmanager

@contextmanager
def timer(name):
    print("开始", name)
    try:
        yield
    finally:
        print("结束", name)

with timer("任务"):
    print("执行中")
```
```output
开始 任务
执行中
结束 任务
```
:::

:::more 异常组和异常注释
并发代码可能同时产生多个异常。3.11 加入的 `ExceptionGroup` 把它们打包抛出，用 `except*` 分别处理。`e.add_note("...")` 可以给异常附加说明，回溯信息里会显示出来。这两个特性主要用于 `asyncio` 这类场景。

```python
try:
    raise ExceptionGroup("批量失败", [ValueError("a"), TypeError("b")])
except* ValueError as group:
    print(len(group.exceptions))  # => 1
except* TypeError as group:
    print(len(group.exceptions))  # => 1
```
:::

:::recap
- `except` 对应 `catch`，`else` 在没有异常时执行，`finally` 始终执行
- 没有受检异常，也没有 `throws`，习惯先做再处理错误
- `raise 新异常 from 原异常` 保留异常链，`from None` 隐藏原异常
- `assert` 只用于内部检查，`-O` 运行时会被跳过
- 自定义异常继承 `Exception`，类名以 `Error` 结尾
- 资源一律用 `with` 管理，对应 `try-with-resources` 和 `use`
:::
