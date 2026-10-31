---
id: functions-and-decorators
part: 函数与数据
title: 函数
lede: 默认参数和关键字参数让 Python 函数比 Java 方法灵活得多，也带来一个必须知道的陷阱。
source: 定义函数 | controlflow.html ; 作用域和命名空间 | classes.html
seo_title: Python 函数教程：默认参数、*args、lambda、装饰器，对比 Java 和 Kotlin
seo_description: 讲解 Python 函数的默认参数陷阱、关键字参数、*args 和 **kwargs、闭包、装饰器和类型注解，并说明 Python 装饰器和 Java 注解的区别。
---

## 定义函数 {#def}

`def` 定义函数。参数和返回值都不写类型，没有 `return` 时返回 `None`。

:::compare 函数定义
```python
def add(a, b):
    """返回两数之和。"""
    return a + b

print(add(2, 3))      # => 5
print(add("a", "b"))  # => ab
```
```java
static int add(int a, int b) {
    return a + b;
}

System.out.println(add(2, 3));  // => 5
```
```kotlin
fun add(a: Int, b: Int) = a + b

println(add(2, 3))  // => 5
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 定义关键字 | `def` | 没有，直接写返回类型 | `fun` |
| 参数类型 | 可选 | 必须写 | 必须写 |
| 返回类型 | 可选 | 必须写 | 单表达式函数可省略 |
| 没有返回值 | 返回 `None` | `void` | `Unit` |
| 定义位置 | 文件顶层 | 类里 | = |

> 要点: 只要 `a + b` 这个操作成立，函数就能运行，这叫鸭子类型。函数体第一行的字符串是文档字符串，`help(add)` 能看到它。
:::

函数是普通对象，可以赋值、传参和返回。写 `f = add` 之后，`f(2, 3)` 和 `add(2, 3)` 完全一样。

## 默认参数和关键字参数 {#args}

调用时可以写参数名，这样可以跳过中间的默认参数，也不用记顺序。

:::compare 默认值和命名调用
```python
def connect(host, port=80, timeout=30):
    return f"{host}:{port} {timeout}s"

print(connect("a.com"))
print(connect("a.com", timeout=5))
print(connect(port=443, host="b.com"))
```
```java
static String connect(String host) {
    return connect(host, 80, 30);
}
static String connect(
        String host, int port, int timeout) {
    return host + ":" + port + " " + timeout + "s";
}

System.out.println(connect("a.com"));
```
```kotlin
fun connect(
    host: String, port: Int = 80, timeout: Int = 30
) = "$host:$port ${timeout}s"

println(connect("a.com"))
println(connect("a.com", timeout = 5))
println(connect(port = 443, host = "b.com"))
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 默认参数 | `port=80` | 不支持，靠方法重载 | `port: Int = 80` |
| 命名调用 | `timeout=5` | 不支持 | `timeout = 5` |
| 跳过中间参数 | 支持 | 不支持 | = |
| 调用顺序 | 位置参数在前，命名参数在后 | 只能按位置传 | 名字可以穿插，但位置要对应 |

> 要点: 这是 Python 和 Kotlin 最接近的地方之一。没有默认参数的语言通常用重载或 Builder 模式。
:::

:::compare 默认值只计算一次
```python
def bad(x, items=[]):
    items.append(x)
    return items

print(bad(1))  # => [1]
print(bad(2))  # => [1, 2]

def good(x, items=None):
    if items is None:
        items = []
    items.append(x)
    return items

print(good(2))  # => [2]
```
```java
static List<Integer> add(int x) {
    return add(x, new ArrayList<>());
}
static List<Integer> add(
        int x, List<Integer> items) {
    items.add(x);
    return items;
}

System.out.println(add(1));  // => [1]
System.out.println(add(2));  // => [2]
```
```kotlin
fun add(
    x: Int,
    items: MutableList<Int> = mutableListOf()
): MutableList<Int> {
    items.add(x)
    return items
}

println(add(1))  // => [1]
println(add(2))  // => [2]
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 默认值何时计算 | `def` 执行时计算一次 | 每次调用重载方法时 | 每次调用时 |
| 多次调用 | 共用同一个对象 | 每次新建 | 每次新建 |
| 可变默认值 | 写 `None`，在函数体里创建 | 没有这个问题 | 没有这个问题 |

> 要点: 列表、字典这类可变对象不能当默认值，这是 Python 最经典的陷阱。
:::

:::more 限定参数的传递方式
参数列表里的 `/` 和 `*` 可以限定传参方式。`/` 之前只能按位置传，`*` 之后只能按名字传。

```python
def send(to, /, body, *, urgent=False):
    return (to, body, urgent)

print(send("ann", "hi", urgent=True))  # => ('ann', 'hi', True)
print(send("ann", body="hi"))          # => ('ann', 'hi', False)
```

写库的时候用得上，日常业务代码很少需要。
:::

## 可变参数和解包 {#varargs}

`*args` 收集多余的位置参数，得到元组。`**kwargs` 收集多余的关键字参数，得到字典。

:::compare 可变参数
```python
def total(*nums, **opts):
    return sum(nums) * opts.get("scale", 1)

print(total(1, 2))           # => 3
print(total(1, 2, scale=10)) # => 30

args = [1, 2, 3]
opts = {"scale": 2}
print(total(*args, **opts))  # => 12
```
```java
static int total(int... nums) {
    return Arrays.stream(nums).sum();
}

System.out.println(total(1, 2));  // => 3
int[] args = {1, 2, 3};
System.out.println(total(args));  // => 6
```
```kotlin
fun total(vararg nums: Int) = nums.sum()

println(total(1, 2))  // => 3
val args = intArrayOf(1, 2, 3)
println(total(*args)) // => 6
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 收集位置参数 | `*nums`，得到元组 | `int... nums`，得到数组 | `vararg nums`，得到数组 |
| 收集命名参数 | `**opts`，得到字典 | 不支持，改传 `Map` | 不支持，改传 `Map` |
| 调用时展开 | `*args`、`**opts` | 直接传数组 | `*args` |

> 要点: `*` 把序列展开成位置参数，`**` 把字典展开成关键字参数，定义和调用用的是同一对符号。
:::

## Lambda 和闭包 {#lambda}

`lambda` 是单表达式的匿名函数。逻辑超过一个表达式时，直接在函数里定义一个内部函数。

:::compare 传递函数
```python
words = ["pear", "fig", "apple"]

words.sort(key=lambda w: len(w))
print(words)  # => ['fig', 'pear', 'apple']

words.sort(key=len)   # 函数本身也能传
square = lambda x: x * x
print(square(4))      # => 16
```
```java
var words = new ArrayList<>(
    List.of("pear", "fig", "apple"));

words.sort(Comparator.comparing(String::length));
System.out.println(words);  // => [fig, pear, apple]

Function<Integer, Integer> square = x -> x * x;
System.out.println(square.apply(4));  // => 16
```
```kotlin
val words = mutableListOf("pear", "fig", "apple")

words.sortBy { it.length }
println(words)  // => [fig, pear, apple]

val square = { x: Int -> x * x }
println(square(4))  // => 16
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 语法 | `lambda x: x * x` | `x -> x * x` | `{ x -> x * x }` |
| 函数体 | 只能一个表达式 | 表达式或代码块 | 可以写多条语句 |
| 单参数简写 | 没有 | 没有 | `it` |
| 传已有函数 | `key=len` | `String::length` | `String::length` |
| 调用方式 | `square(4)` | `square.apply(4)` | `square(4)` |

> 要点: 逻辑超过一个表达式时，直接在函数内部 `def` 一个函数再传出去。
:::

## 作用域 {#scope}

名字按 LEGB 顺序查找：局部、外层函数、全局、内置。函数、类、模块和推导式会创建作用域，`if`、`for`、`while` 不会。

:::compare if 和 for 不创建作用域
```python
for i in range(3):
    last = i * 2

print(i, last)  # => 2 4

if True:
    msg = "可见"
print(msg)      # => 可见
```
```java
int last = 0;
for (int i = 0; i < 3; i++) {
    last = i * 2;
}
// System.out.println(i);  编译错误
System.out.println(last);  // => 4
```
```kotlin
var last = 0
for (i in 0 until 3) {
    last = i * 2
}
// println(i)  编译错误
println(last)  // => 4
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 块级作用域 | 没有 | 有 | 有 |
| 循环变量 | 循环后仍然存在 | 循环后失效 | 循环后失效 |
| 创建作用域的结构 | 函数、类、模块、推导式 | 任何花括号 | 任何花括号 |
| 声明变量 | 首次赋值时创建 | 必须先声明 | 必须先声明 |

> 要点: 这一点最容易被忽略。注意循环变量可能遮盖外面的同名变量。
:::

在函数里给变量赋值，默认创建局部变量。要修改外层的变量，必须先声明。

:::compare 修改外层变量
```python
def make_counter():
    n = 0
    def step():
        nonlocal n
        n += 1
        return n
    return step

c = make_counter()
c()
print(c())  # => 2
```
```java
§ import java.util.concurrent.atomic.AtomicInteger;
static Supplier<Integer> makeCounter() {
    var n = new AtomicInteger();
    return () -> n.incrementAndGet();
}

var c = makeCounter();
c.get();
System.out.println(c.get());  // => 2
```
```kotlin
fun makeCounter(): () -> Int {
    var n = 0
    return { ++n }
}

val c = makeCounter()
c()
println(c())  // => 2
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 修改外层局部变量 | 声明 `nonlocal` | 不允许，要借助对象 | 直接修改 |
| 修改全局变量 | 声明 `global` | 直接修改静态字段 | 直接修改 |
| 闭包捕获 | 捕获变量本身 | 捕获值，变量必须实际不可变 | 捕获变量本身 |
| 读取外层变量 | 直接读取 | = | = |

> 要点: 不声明 `nonlocal` 时，`n += 1` 会抛 `UnboundLocalError`，因为赋值让 `n` 变成了局部变量。
:::

## 装饰器 {#decorators}

前面已经见过 `@property`、`@dataclass` 这些写法，它们都是装饰器。装饰器是一个接收函数、返回新函数的函数，`@logged` 写在 `def` 上方，等价于定义后执行 `add = logged(add)`。

:::compare 给函数加上日志
```python
import functools

def logged(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("调用", func.__name__)
        return func(*args, **kwargs)
    return wrapper

@logged
def add(a, b):
    return a + b

print(add(1, 2))  # => 3
```
```java
static <A, B> Function<A, B> logged(
        String name, Function<A, B> func) {
    return arg -> {
        System.out.println("调用 " + name);
        return func.apply(arg);
    };
}

Function<Integer, Integer> twice =
    logged("twice", x -> x * 2);
System.out.println(twice.apply(2));  // => 4
```
```kotlin
fun <A, B> logged(
    name: String, func: (A) -> B
): (A) -> B = { arg ->
    println("调用 $name")
    func(arg)
}

val twice = logged("twice") { x: Int -> x * 2 }
println(twice(2))  // => 4
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| `@` 的含义 | 调用函数，替换被装饰的函数 | 注解，只是元数据 | 注解，只是元数据 |
| 谁来生效 | 定义函数时立即执行 | 编译器或框架读取注解 | 编译器或框架读取注解 |
| 实现横切逻辑 | 写一个装饰器 | 动态代理或 AOP | 高阶函数或 AOP |
| 底层思路 | 函数包裹函数 | = | = |

> 要点: `@` 在 Python 里会真正替换函数，这和 Java、Kotlin 的注解完全不同。`@functools.wraps` 保留原函数的名字和文档，写装饰器时都要加上。
:::

`functools` 里有几个现成的工具：`@lru_cache` 给函数加缓存，`partial` 固定函数的部分参数，`reduce` 做累积计算。

## 文档字符串和类型注解 {#docs}

类型注解是可选的，解释器运行时完全不检查。它的价值在于 IDE 补全和 `mypy`、`pyright` 这样的静态检查工具。

:::compare 带类型的函数
```python
def area(w: float, h: float = 1.0) -> float:
    """计算矩形面积。

    首行写摘要，空一行后再写细节。
    """
    return w * h

print(area(2, 3))      # => 6
print(area("ab", 2))   # => abab
```
```java
/** 计算矩形面积。 */
static double area(double w, double h) {
    return w * h;
}

System.out.println(area(2, 3));  // => 6.0
```
```kotlin
/** 计算矩形面积。 */
fun area(w: Double, h: Double = 1.0): Double =
    w * h

println(area(2.0, 3.0))  // => 6.0
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 类型标注 | 可选 | 必须写 | 参数必须写，其余可推断 |
| 何时检查 | 运行时不检查 | 编译时 | 编译时 |
| 检查工具 | `mypy`、`pyright` | `javac` | `kotlinc` |
| 文档写法 | 函数体内首行字符串 | 函数前的 `/** */` | 函数前的 `/** */` |

> 要点: `area("ab", 2)` 能运行，说明注解不影响运行结果。新项目建议从一开始就写注解。
:::

注解保存在函数的 `__annotations__` 属性里，框架可以在运行时读取，FastAPI 和 pydantic 就靠它工作。

### 常用的类型写法

:::compare 泛型、可空和函数类型
```python
from collections.abc import Callable

def first[T](xs: list[T]) -> T | None:
    return xs[0] if xs else None

def call(f: Callable[[int], int], x: int) -> int:
    return f(x)

ages: dict[str, int] = {"Ann": 30}

print(first([1, 2]))             # => 1
print(first([]))                 # => None
print(call(lambda n: n + 1, 1))  # => 2
```
```java
static <T> Optional<T> first(List<T> xs) {
    return xs.stream().findFirst();
}

static int call(IntUnaryOperator f, int x) {
    return f.applyAsInt(x);
}

Map<String, Integer> ages = Map.of("Ann", 30);

System.out.println(first(List.of(1, 2)));  // => Optional[1]
System.out.println(call(n -> n + 1, 1));   // => 2
```
```kotlin
fun <T> first(xs: List<T>): T? = xs.firstOrNull()

fun call(f: (Int) -> Int, x: Int): Int = f(x)

val ages: Map<String, Int> = mapOf("Ann" to 30)

println(first(listOf(1, 2)))      // => 1
println(first(emptyList<Int>()))  // => null
println(call({ it + 1 }, 1))      // => 2
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 容器类型 | `list[int]`、`dict[str, int]` | `List<Integer>`、`Map<String, Integer>` | `List<Int>`、`Map<String, Int>` |
| 可能为空 | `T \| None` | `Optional<T>` 或 `@Nullable` | `T?` |
| 泛型函数 | `def f[T](x: T)` | `<T> void f(T x)` | `fun <T> f(x: T)` |
| 函数类型 | `Callable[[int], int]` | `Function`、`IntUnaryOperator` 等接口 | `(Int) -> Int` |
| 类型别名 | `type Ids = list[int]` | 不支持 | `typealias Ids = List<Int>` |
| 空值保护 | 只有类型检查工具提示 | 只有工具提示 | 编译器强制 |

> 要点: `def f[T]` 和 `type` 语句是 3.12 的新语法。老代码里常见 `Optional[str]`、`List[int]` 和 `TypeVar`，含义相同。
:::

## 编码风格 {#style}

Python 社区统一遵循 PEP 8 规范。写之前先记住下面的命名习惯，它们和 Java、Kotlin 有明显区别。格式化工具用 `ruff format` 或 `black`。

:::map 命名与风格
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `snake_case` | `camelCase` | `camelCase` | 函数和变量 |
| `PascalCase` | `PascalCase` | `PascalCase` | 类名 |
| `UPPER_CASE` | `UPPER_CASE` | `UPPER_CASE` | 常量 |
| `snake_case.py` | `PascalCase.java` | `PascalCase.kt` | 文件名 |
| `self` | `this` | `this` | Python 要显式写在参数里 |
| `_internal` | `private` | `private` | Python 只是约定 |
| 每行不超过 79 字符 | 100 到 120 字符 | 100 到 120 字符 | 很多团队会放宽到 88 或 120 |
:::

:::recap
- 默认参数和关键字参数的用法和 Kotlin 几乎相同
- 默认值只计算一次，可变对象一律用 `None` 代替
- `*args` 收集成元组，`**kwargs` 收集成字典，调用时可以反向展开
- 只有函数、类、模块创建作用域，`for` 和 `if` 不创建
- 修改外层变量要声明 `nonlocal` 或 `global`
- 装饰器是包裹函数的函数，`@` 会真正替换函数，和 Java 注解不同
- 类型注解运行时不检查，要配合 `mypy` 或 `pyright`
- 可空类型写 `T | None`，3.12 起泛型函数写 `def f[T](x: T)`
:::
