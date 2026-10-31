---
id: control-flow
part: 语言基础
title: 控制流
lede: 条件、循环和模式匹配。Python 只有 for-each 式的循环，习惯后比下标循环更省事。
source: 更多控制流工具 | controlflow.html ; 深入条件控制 | datastructures.html
seo_title: Python 控制流：if、for 和 match，对比 Java 与 Kotlin
seo_description: 讲解 Python 的条件判断、for 循环、range、enumerate、zip、循环 else 和 match 模式匹配，并对比 Java switch 和 Kotlin when 的写法与区别。
---

## 条件判断 {#if}

`else if` 在 Python 里写成 `elif`。条件不用括号，`&&`、`||`、`!` 写成 `and`、`or`、`not`，优先级从高到低是 `not`、`and`、`or`。成员判断用 `in` 和 `not in`，身份判断用 `is` 和 `is not`。

:::compare if / elif / else
```python
score = 85
if score >= 90:
    grade = "A"
elif score >= 60:
    grade = "B"
else:
    grade = "C"
print(grade)  # => B
```
```java
int score = 85;
String grade;
if (score >= 90) {
    grade = "A";
} else if (score >= 60) {
    grade = "B";
} else {
    grade = "C";
}
System.out.println(grade);  // => B
```
```kotlin
val score = 85
val grade = when {
    score >= 90 -> "A"
    score >= 60 -> "B"
    else -> "C"
}
println(grade)  // => B
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 多分支 | `elif` | `else if` | `else if` 或 `when` |
| 条件括号 | 不写 | 必须写 | 必须写 |
| 能否当值用 | 不能，是语句 | 不能，是语句 | 可以，是表达式 |
| 判断顺序 | 依次判断，执行第一个命中的分支 | = | = |

> 要点: Python 需要根据条件得到一个值时，用下面的条件表达式。
:::

:::compare 条件表达式和链式比较
```python
age = 20
label = "成年" if age >= 18 else "未成年"
print(label)          # => 成年
print(0 < age < 30)   # => True
```
```java
int age = 20;
var label = age >= 18 ? "成年" : "未成年";
System.out.println(label);  // => 成年
System.out.println(0 < age && age < 30);  // => true
```
```kotlin
val age = 20
val label = if (age >= 18) "成年" else "未成年"
println(label)        // => 成年
println(age in 1..29) // => true
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 条件表达式 | `x if c else y` | `c ? x : y` | `if (c) x else y` |
| 阅读顺序 | 先看结果，再看条件 | 先看条件，再看结果 | 先看条件，再看结果 |
| 区间判断 | `0 < x < 30` | `0 < x && x < 30` | `x in 1..29` |
| 短路求值 | 支持 | = | = |

> 要点: 比较运算可以连写，`0 < x < 30` 和数学写法一样。
:::

### 真值

任何对象都能放进 `if`。`None`、`False`、`0`、`0.0`、`""`、`[]`、`{}` 都算假，其余都算真。

:::compare 判空和默认值
```python
items = []
if not items:
    print("空列表")     # => 空列表

name = ""
print(name or "匿名")   # => 匿名
```
```java
var items = new ArrayList<String>();
if (items.isEmpty()) {
    System.out.println("空列表");  // => 空列表
}
var name = "";
var shown = name.isEmpty() ? "匿名" : name;
System.out.println(shown);  // => 匿名
```
```kotlin
val items = emptyList<String>()
if (items.isEmpty()) {
    println("空列表")   // => 空列表
}
val name = ""
println(name.ifEmpty { "匿名" })  // => 匿名
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 判断容器为空 | `if not items` | `items.isEmpty()` | `items.isEmpty()` |
| 条件的类型 | 任何对象 | 必须是 `boolean` | 必须是 `Boolean` |
| 空值取默认值 | `x if x is not None else d` | `Objects.requireNonNullElse` | `x ?: d` |
| 逻辑运算结果 | `or`、`and` 返回操作数本身 | 返回布尔值 | 返回布尔值 |

> 要点: `or` 把 `0`、`""` 也当成假，这是常见的坑。要区分 `None` 和 `0` 时，写 `if x is None`。
:::

### 赋值表达式

`:=` 在表达式内部完成赋值，因为长得像海象，也叫海象运算符。它常用于先取值再判断的场景，能少写一行。

:::compare 先取值再判断
```python
import re

text = "order-42"
if (m := re.search(r"\d+", text)):
    print(m.group())   # => 42
```
```java
var text = "order-42";
var m = Pattern.compile("\\d+").matcher(text);
if (m.find()) {
    System.out.println(m.group());  // => 42
}
```
```kotlin
val text = "order-42"
Regex("""\d+""").find(text)?.let {
    println(it.value)   // => 42
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 写法 | 条件里用 `:=` 赋值 | 先赋值，再判断 | `?.let` 处理非空结果 |
| 变量作用域 | 变量在 `if` 之后仍然存在 | 变量声明在 `if` 之外 | `it` 只在代码块内有效 |

> 要点: 普通赋值 `=` 不能写在 `if` 条件里，这能避免把 `==` 写成 `=` 的错误。`:=` 两边通常要加括号。
:::

## 循环 {#for}

`for` 只有一种形式，遍历任何可迭代对象。需要数字序列时用 `range()`。`while` 和其他语言相同，但没有 `do-while`。

:::compare 数字循环
```python
for i in range(3):
    print(i)        # 0 1 2

for i in range(10, 0, -3):
    print(i)        # 10 7 4 1

for ch in "abc":
    print(ch)
```
```java
for (int i = 0; i < 3; i++) {
    System.out.println(i);
}
for (int i = 10; i > 0; i -= 3) {
    System.out.println(i);
}
for (char ch : "abc".toCharArray()) {
    System.out.println(ch);
}
```
```kotlin
for (i in 0 until 3) {
    println(i)
}
for (i in 10 downTo 1 step 3) {
    println(i)
}
for (ch in "abc") {
    println(ch)
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 循环形式 | 只有遍历式 `for` | 有三段式和遍历式 | = |
| 不含上界 | `range(3)` | `i < 3` | `0 until 3` |
| 倒序和步长 | `range(10, 0, -3)` | `i -= 3` | `10 downTo 1 step 3` |
| `do-while` | 没有 | 有 | 有 |
| 遍历字符串 | 直接遍历 | 先转字符数组 | = |

> 要点: `range(起, 止, 步长)` 左闭右开，而且是惰性的。需要真正的列表时写 `list(range(3))`。
:::

遍历时经常要同时拿到下标，或者并排遍历两个列表。Python 用两个内置函数解决，不用手写下标。

:::compare 带下标遍历和并排遍历
```python
names = ["Ann", "Bob"]
ages = [30, 25]

for i, name in enumerate(names):
    print(i, name)

for name, age in zip(names, ages):
    print(name, age)
```
```java
var names = List.of("Ann", "Bob");
var ages = List.of(30, 25);

for (int i = 0; i < names.size(); i++) {
    System.out.println(i + " " + names.get(i));
}
for (int i = 0; i < names.size(); i++) {
    System.out.println(
        names.get(i) + " " + ages.get(i));
}
```
```kotlin
val names = listOf("Ann", "Bob")
val ages = listOf(30, 25)

for ((i, name) in names.withIndex()) {
    println("$i $name")
}
for ((name, age) in names.zip(ages)) {
    println("$name $age")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 带下标遍历 | `enumerate(xs)` | 下标循环 | `xs.withIndex()` |
| 并排遍历 | `zip(a, b)` | 下标循环 | `a.zip(b)` |
| 长度不一致 | 以最短的为准 | 需要自己处理 | = |
| 循环里解构 | `for i, x in ...` | 不支持 | `for ((i, x) in ...)` |

> 要点: 看到 `for i in range(len(xs))` 基本都可以改成 `enumerate`。
:::

:::warn 遍历时别修改集合
遍历列表时增删元素会跳过元素，而且不报错。遍历字典时改变大小会抛 `RuntimeError`。Java 在这两种情况下都抛 `ConcurrentModificationException`。稳妥的做法是遍历副本 `for x in xs.copy()`，或者用推导式生成新列表。
:::

## break、continue 和循环的 else {#loop-else}

`break` 和 `continue` 的含义不变，但 Python 没有带标签的 `break`。循环还可以带一个 `else`，它在循环没有被 `break` 打断时执行，适合写查找逻辑。

:::compare 查找失败时的处理
```python
for n in [3, 5, 7]:
    if n % 2 == 0:
        print("找到偶数", n)
        break
else:
    print("全是奇数")   # => 全是奇数
```
```java
boolean found = false;
for (int n : List.of(3, 5, 7)) {
    if (n % 2 == 0) {
        System.out.println("找到偶数 " + n);
        found = true;
        break;
    }
}
if (!found) {
    System.out.println("全是奇数");  // => 全是奇数
}
```
```kotlin
val even = listOf(3, 5, 7)
    .firstOrNull { it % 2 == 0 }
if (even != null) {
    println("找到偶数 $even")
} else {
    println("全是奇数")  // => 全是奇数
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 常见写法 | 循环的 `else` | 标志变量 | `firstOrNull` |
| 循环 `else` | 没有 `break` 时执行 | 没有这个语法 | 没有这个语法 |
| 带标签跳出 | 不支持 | `break label` | `break@label` |
| `break`、`continue` | 含义相同 | = | = |

> 要点: `else` 对齐的是 `for`，不是 `if`。它省掉了 `found` 这样的标志变量。
:::

`pass` 是空语句，语法上需要代码块但什么都不做时用它，比如 `class Empty: pass`。对应 Java 和 Kotlin 的空花括号。

## match 语句 {#match}

`match` 是 3.10 加入的结构化模式匹配，能同时判断形状并提取值。分支不会贯穿，`case _` 相当于 `default`。

:::compare 模式匹配
```python
def where(point):
    match point:
        case (0, 0):
            return "原点"
        case (x, 0):
            return f"X 轴，x={x}"
        case (x, y) if x == y:
            return "对角线"
        case _:
            return "其他"

print(where((3, 0)))  # => X 轴，x=3
```
```java
record Point(int x, int y) {}

static String where(Point p) {
    return switch (p) {
        case Point(int x, int y)
            when x == 0 && y == 0 -> "原点";
        case Point(int x, int y)
            when y == 0 -> "X 轴，x=" + x;
        case Point(int x, int y)
            when x == y -> "对角线";
        default -> "其他";
    };
}
§ System.out.println(where(new Point(3, 0)));  // => X 轴，x=3
```
```kotlin
fun where(p: Pair<Int, Int>): String {
    val (x, y) = p
    return when {
        x == 0 && y == 0 -> "原点"
        y == 0 -> "X 轴，x=$x"
        x == y -> "对角线"
        else -> "其他"
    }
}
println(where(3 to 0))  // => X 轴，x=3
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 语法 | `match` / `case` | `switch` + 记录模式 | `when` |
| 版本要求 | Python 3.10 起 | Java 21 起 | 所有版本 |
| 结构解构 | 元组、字典、类实例都支持 | 支持 `record` | 不支持，要先解构再判断 |
| 守卫条件 | `case ... if c` | `case ... when c` | 写在 `when` 的分支条件里 |
| 默认分支 | `case _` | `default` | `else` |
| 分支贯穿 | 不贯穿 | 箭头写法不贯穿，冒号写法会贯穿 | = |

> 要点: `case RED:` 里的裸名字会绑定成新变量，而不是和常量比较。比较常量要写带点的名字，如 `case Color.RED:`。
:::

:::more match 的其他模式
除了元组，`match` 还能匹配多个值、序列、字典和类实例。

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

def check(value):
    match value:
        case "quit" | "exit":      # 多个值
            return "退出"
        case [first, *rest]:       # 序列，*rest 收集剩余元素
            return f"还剩 {len(rest)} 项"
        case {"name": name}:       # 字典，只要求包含这个键
            return f"名字是 {name}"
        case Point(x=0, y=y):      # 类实例
            return f"Y 轴，y={y}"
        case int() as n if n > 0:  # 类型、as 绑定和守卫
            return f"正整数 {n}"
        case _:
            return "其他"

print(check("exit"))           # => 退出
print(check([1, 2, 3]))        # => 还剩 2 项
print(check({"name": "Ann"}))  # => 名字是 Ann
print(check(Point(0, 5)))      # => Y 轴，y=5
print(check(7))                # => 正整数 7
```
:::

:::map 控制流速查
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `elif` | `else if` | `else if` | |
| `and` / `or` / `not` | `&&` / `\|\|` / `!` | `&&` / `\|\|` / `!` | |
| `x if c else y` | `c ? x : y` | `if (c) x else y` | |
| `for i in range(n)` | `for (int i = 0; i < n; i++)` | `for (i in 0 until n)` | |
| `enumerate(xs)` | 下标循环 | `xs.withIndex()` | |
| `zip(a, b)` | 下标循环 | `a.zip(b)` | |
| `x not in xs` | `!xs.contains(x)` | `x !in xs` | |
| `pass` | `{}` | `{}` | |
| `match` / `case` | `switch` | `when` | |
| 循环的 `else` | 标志变量 | `firstOrNull` 等 | |
:::

:::recap
- `elif` 代替 `else if`，逻辑运算符写成 `and`、`or`、`not`
- 空容器、`0`、`""`、`None` 都算假，判空写 `if not xs`
- `:=` 在表达式内部赋值，常用于先取值再判断
- `for` 只遍历序列，数字循环用 `range`，下标用 `enumerate`，并排用 `zip`
- 循环的 `else` 在没有 `break` 时执行
- `match` 能按结构匹配并提取值，比较常量时要写带点的名字
:::
