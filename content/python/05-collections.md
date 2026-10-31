---
id: data-structures
part: 函数与数据
title: 数据结构
lede: 列表、元组、集合和字典，再加上推导式。这一章的内容在日常代码里出现得最频繁。
source: 数据结构 | datastructures.html
seo_title: Python 数据结构：推导式、字典和集合，对比 Java
seo_description: 讲解 Python 的 list、tuple、set、dict 和列表推导式，并对比 Java Stream 和 Kotlin 集合操作，帮你把 ArrayList、HashMap 的经验用到 Python 上。
---

## 四种内置容器 {#overview}

Python 把最常用的四种容器做成了内置类型，都有字面量语法，不用导入任何东西。

:::map 容器类型
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `list`：`[1, 2]` | `ArrayList` | `MutableList` | 有序、可变 |
| `tuple`：`(1, 2)` | `record` / `List.of` | `Pair` / `data class` | 有序、不可变 |
| `set`：`{1, 2}` | `HashSet` | `MutableSet` | 无序、元素唯一 |
| `dict`：`{"a": 1}` | `LinkedHashMap` | `LinkedHashMap` | 键值对，保持插入顺序 |
| `collections.deque` | `ArrayDeque` | `ArrayDeque` | 双端队列 |
:::

## 列表方法 {#list-methods}

列表的方法基本都能对应上，下表列出最常用的几个。需要注意 `sort()` 原地排序并返回 `None`，所以 `xs = xs.sort()` 会把列表弄丢。想要新列表用 `sorted(xs)`。

:::map 列表操作
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `xs.append(x)` | `xs.add(x)` | `xs.add(x)` | 加到末尾 |
| `xs.extend(ys)` | `xs.addAll(ys)` | `xs.addAll(ys)` | 合并另一个列表 |
| `xs.insert(i, x)` | `xs.add(i, x)` | `xs.add(i, x)` | |
| `xs.remove(x)` | `xs.remove(x)` | `xs.remove(x)` | Python 找不到时抛 `ValueError` |
| `xs.pop()` | `xs.removeLast()` | `xs.removeLast()` | 删除并返回末尾元素，Java 21 起可用 |
| `xs.pop(0)` | `xs.remove(0)` | `xs.removeAt(0)` | 按下标删除 |
| `xs.index(x)` | `xs.indexOf(x)` | `xs.indexOf(x)` | Python 找不到时抛异常，而不是返回 -1 |
| `xs.sort()` | `Collections.sort(xs)` | `xs.sort()` | 原地排序 |
| `sorted(xs)` | `xs.stream().sorted()` | `xs.sorted()` | 返回新列表 |
| `xs.reverse()` | `Collections.reverse(xs)` | `xs.reverse()` | 原地反转 |
| `xs.count(x)` | `Collections.frequency(xs, x)` | `xs.count { it == x }` | 统计出现次数 |
| `xs.copy()` | `new ArrayList<>(xs)` | `xs.toMutableList()` | 浅拷贝 |
| `xs.clear()` | `xs.clear()` | `xs.clear()` | 清空 |
| `del xs[0]` | `xs.remove(0)` | `xs.removeAt(0)` | `del` 也能删切片：`del xs[1:3]` |
:::

:::compare 栈和队列
```python
from collections import deque

stack = [1, 2]
stack.append(3)
print(stack.pop())       # => 3

queue = deque(["a", "b"])
queue.append("c")
print(queue.popleft())   # => a
```
```java
var stack = new ArrayDeque<Integer>();
stack.push(1);
stack.push(2);
System.out.println(stack.pop());  // => 2

var queue = new ArrayDeque<>(List.of("a", "b"));
queue.addLast("c");
System.out.println(queue.pollFirst());  // => a
```
```kotlin
val stack = ArrayDeque(listOf(1, 2))
stack.addLast(3)
println(stack.removeLast())  // => 3

val queue = ArrayDeque(listOf("a", "b"))
queue.addLast("c")
println(queue.removeFirst()) // => a
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 栈 | `list` 的 `append`、`pop` | `ArrayDeque` 的 `push`、`pop` | `ArrayDeque` 的 `addLast`、`removeLast` |
| 队列 | `deque` 的 `append`、`popleft` | `ArrayDeque` 的 `addLast`、`pollFirst` | `ArrayDeque` 的 `addLast`、`removeFirst` |
| 需要导入 | 栈不用，`deque` 要导入 | 要导入 | 不用 |
| 两端操作 | 双端队列都是 O(1) | = | = |

> 要点: 不要用 `xs.pop(0)` 当队列，它要移动全部元素，是 O(n) 操作。
:::

## 推导式 {#comprehensions}

推导式把 `map` 和 `filter` 合成一行。Python 代码里到处都是它，一定要熟练。

:::compare 列表推导式
```python
nums = [1, 2, 3, 4, 5, 6]
squares = [n * n for n in nums if n % 2 == 0]
print(squares)  # => [4, 16, 36]
```
```java
var nums = List.of(1, 2, 3, 4, 5, 6);
var squares = nums.stream()
    .filter(n -> n % 2 == 0)
    .map(n -> n * n)
    .toList();
System.out.println(squares);  // => [4, 16, 36]
```
```kotlin
val nums = listOf(1, 2, 3, 4, 5, 6)
val squares = nums
    .filter { it % 2 == 0 }
    .map { it * it }
println(squares)  // => [4, 16, 36]
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 写法 | 一个表达式写完 | Stream 链式调用 | 集合函数链式调用 |
| 过滤 | 末尾的 `if` | `.filter` | `.filter` |
| 转换 | 开头的表达式 | `.map` | `.map` |
| 得到列表 | 直接得到 | 要调用 `.toList()` | 直接得到 |
| 惰性版本 | 生成器表达式 | Stream 本身惰性 | `asSequence()` |

> 要点: 语法是「表达式 for 变量 in 序列 if 条件」。Python 也有 `map()` 和 `filter()`，但社区更偏爱推导式。
:::

:::compare 字典、集合和嵌套推导式
```python
words = ["hi", "hey", "yo"]
lengths = {w: len(w) for w in words}
print(lengths)  # => {'hi': 2, 'hey': 3, 'yo': 2}

first = {w[0] for w in words}
print(sorted(first))  # => ['h', 'y']

grid = [[1, 2], [3, 4]]
flat = [x for row in grid for x in row]
print(flat)  # => [1, 2, 3, 4]
```
```java
var words = List.of("hi", "hey", "yo");
var lengths = words.stream().collect(
    Collectors.toMap(w -> w, String::length));
System.out.println(lengths.get("hey"));  // => 3

var grid = List.of(List.of(1, 2), List.of(3, 4));
var flat = grid.stream()
    .flatMap(List::stream).toList();
System.out.println(flat);  // => [1, 2, 3, 4]
```
```kotlin
val words = listOf("hi", "hey", "yo")
val lengths = words.associateWith { it.length }
println(lengths)  // => {hi=2, hey=3, yo=2}

val first = words.map { it[0] }.toSet()
println(first)  // => [h, y]

val grid = listOf(listOf(1, 2), listOf(3, 4))
println(grid.flatten())  // => [1, 2, 3, 4]
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 生成字典 | `{w: len(w) for w in xs}` | `Collectors.toMap` | `associateWith` |
| 生成集合 | `{w[0] for w in xs}` | `Collectors.toSet` | `.toSet()` |
| 展平嵌套 | `[x for row in g for x in row]` | `flatMap` | `flatten()` |

> 要点: 嵌套时 `for` 的顺序和写普通循环时相同。超过两层就不好读了，这时改回普通循环。
:::

`zip(*grid)` 可以转置二维列表，`*` 把每一行展开成一个参数。

## 元组和解包 {#tuples}

元组是不可变的序列，常用来临时组合几个值。函数返回多个值时，实际返回的就是元组。

:::compare 多返回值和解包
```python
def min_max(xs):
    return min(xs), max(xs)

low, high = min_max([3, 1, 2])
print(low, high)     # => 1 3

first, *rest = [1, 2, 3]
print(rest)          # => [2, 3]

point = (3, 4)
x, y = point
print(x + y)         # => 7
```
```java
record MinMax(int low, int high) {}

static MinMax minMax(List<Integer> xs) {
    return new MinMax(
        Collections.min(xs),
        Collections.max(xs));
}

var r = minMax(List.of(3, 1, 2));
System.out.println(r.low() + " " + r.high());  // => 1 3
```
```kotlin
fun minMax(xs: List<Int>) =
    xs.min() to xs.max()

val (low, high) = minMax(listOf(3, 1, 2))
println("$low $high")  // => 1 3

val nums = listOf(1, 2, 3)
val rest = nums.drop(1)
println(rest)          // => [2, 3]
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 多返回值 | 直接返回元组 | 定义 `record` | `Pair`、`Triple` 或 `data class` |
| 解构 | `a, b = f()` | 只能用在模式匹配里 | `val (a, b) = f()` |
| 剩余元素 | `first, *rest = xs` | 不支持 | 不支持，用 `drop` |
| 不可变性 | 创建后不能修改 | = | = |

> 要点: 逗号才是元组的标志，括号可以省略，所以单元素元组要写成 `(1,)`。元组能当字典的键，列表不行。
:::

需要给字段起名时，用 `collections.namedtuple` 或第 8 章的 `dataclass`，比记住下标更清楚。

## 集合 {#sets}

`set` 存放不重复的元素，判断是否存在是 O(1)。交并差都有运算符。注意 `{}` 是空字典，空集合要写 `set()`。

:::compare 集合运算
```python
a = {1, 2, 3}
b = {2, 3, 4}
print(a & b)    # => {2, 3}
print(a | b)    # => {1, 2, 3, 4}
print(a - b)    # => {1}
print(2 in a)   # => True
print(len(set("banana")))  # => 3
```
```java
var a = new TreeSet<>(List.of(1, 2, 3));
var b = Set.of(2, 3, 4);

var both = new TreeSet<>(a);
both.retainAll(b);
System.out.println(both);  // => [2, 3]

var all = new TreeSet<>(a);
all.addAll(b);
System.out.println(all);   // => [1, 2, 3, 4]

System.out.println(a.contains(2));  // => true
```
```kotlin
val a = setOf(1, 2, 3)
val b = setOf(2, 3, 4)
println(a intersect b)  // => [2, 3]
println(a union b)      // => [1, 2, 3, 4]
println(a - b)          // => [1]
println(2 in a)         // => true
println("banana".toSet().size)  // => 3
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 交集 | `a & b` | `retainAll`，修改原集合 | `a intersect b` |
| 并集 | `a \| b` | `addAll`，修改原集合 | `a union b` |
| 差集 | `a - b` | `removeAll`，修改原集合 | `a - b` |
| 字面量 | `{1, 2}`，空集合写 `set()` | 没有，用 `Set.of` | 没有，用 `setOf` |
| 元素规则 | 元素不重复 | = | = |

> 要点: 列表去重最短的写法是 `list(set(xs))`，但会丢失顺序。要保留顺序写 `list(dict.fromkeys(xs))`。
:::

## 字典 {#dicts}

`dict` 是 Python 的核心类型，对象属性和模块命名空间都用它实现。从 3.7 起保证按插入顺序遍历。

:::compare 字典基础
```python
ages = {"Ann": 30, "Bob": 25}
ages["Cid"] = 41

print(ages["Ann"])         # => 30
print(ages.get("Dan", 0))  # => 0
print("Bob" in ages)       # => True

del ages["Bob"]
for name, age in ages.items():
    print(name, age)
```
```java
var ages = new LinkedHashMap<String, Integer>();
ages.put("Ann", 30);
ages.put("Bob", 25);

System.out.println(ages.get("Ann"));  // => 30
var dan = ages.getOrDefault("Dan", 0);
System.out.println(dan);              // => 0

ages.remove("Bob");
ages.forEach((name, age) ->
    System.out.println(name + " " + age));
```
```kotlin
val ages = mutableMapOf("Ann" to 30, "Bob" to 25)
ages["Cid"] = 41

println(ages["Ann"])           // => 30
println(ages.getOrDefault("Dan", 0))  // => 0
println("Bob" in ages)         // => true

ages.remove("Bob")
for ((name, age) in ages) {
    println("$name $age")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 键不存在 | `d["x"]` 抛 `KeyError` | `get` 返回 `null` | `d["x"]` 返回 `null` |
| 带默认值读取 | `d.get("x", 0)` | `getOrDefault` | `getOrDefault` |
| 遍历顺序 | 保持插入顺序 | `HashMap` 无序，`LinkedHashMap` 有序 | `mutableMapOf` 保持插入顺序 |
| 字面量 | `{"a": 1}` | 没有，用 `Map.of` | 没有，用 `mapOf("a" to 1)` |
| 写入 | `d["x"] = 1` | `put` | `d["x"] = 1` |

> 要点: 键必须可哈希，常用字符串、数字和元组。列表不能当键。
:::

`dict(a=1, b=2)` 也能创建字典。合并两个字典写 `a | b`，右边的键优先，老代码里常见 `{**a, **b}`。`d.setdefault(k, [])` 在键不存在时写入默认值并返回它。`list(d)` 得到全部键，`sorted(d)` 得到排好序的键。

下面这个词频统计把几种容器串了起来。`Counter` 是 `dict` 的子类，专门用来计数。

:::compare 统计出现最多的单词 {#hero}
```python
from collections import Counter

text = "to be or not to be"
top = Counter(text.split()).most_common(2)
print(top)  # => [('to', 2), ('be', 2)]
```
```java
§ import static java.util.Map.Entry.comparingByValue;
§ import static java.util.Comparator.reverseOrder;
§ import static java.util.stream.Collectors.*;
var text = "to be or not to be";
var top = Arrays.stream(text.split(" "))
    .collect(groupingBy(
        w -> w, LinkedHashMap::new, counting()))
    .entrySet().stream()
    .sorted(comparingByValue(reverseOrder()))
    .limit(2)
    .toList();
System.out.println(top);  // => [to=2, be=2]
```
```kotlin
val text = "to be or not to be"
val top = text.split(" ")
    .groupingBy { it }
    .eachCount()
    .entries
    .sortedByDescending { it.value }
    .take(2)
    .map { it.key to it.value }
println(top)  // => [(to, 2), (be, 2)]
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 计数 | `Counter` 现成可用 | `groupingBy` + `counting` | `groupingBy` + `eachCount` |
| 取前几名 | `most_common(2)` | 排序后 `limit` | 排序后 `take` |
| 需要的步骤 | 一步 | 分组、排序、截取 | 分组、排序、截取 |

> 要点: Python 把常见任务做成了标准库函数，写起来很短。需要定制时再回到普通循环和推导式。
:::

:::more defaultdict 和 sorted 的 key 参数
`collections.defaultdict(list)` 在键不存在时自动创建默认值，对应 Kotlin 的 `getOrPut`。`sorted(d.items(), key=lambda kv: kv[1], reverse=True)` 可以按值给字典排序。需要按多个字段排序时，让 `key` 返回元组即可。
:::

## 循环技巧 {#looping}

下面这些内置函数可以省掉很多手写循环。

:::map 常用内置函数
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `for k, v in d.items()` | `d.forEach((k, v) -> ...)` | `for ((k, v) in d)` | 同时遍历键和值 |
| `sum(xs)` | `stream.mapToInt(i -> i).sum()` | `xs.sum()` | |
| `min(xs)` / `max(xs)` | `Collections.min(xs)` | `xs.min()` | |
| `any(x > 0 for x in xs)` | `stream.anyMatch(...)` | `xs.any { it > 0 }` | |
| `all(x > 0 for x in xs)` | `stream.allMatch(...)` | `xs.all { it > 0 }` | |
| `reversed(xs)` | `xs.reversed()` | `xs.reversed()` | Python 返回迭代器，Java 21 起可用 |
| `sorted(xs, key=f)` | `stream.sorted(cmp)` | `xs.sortedBy(f)` | |
:::

## 相等和同一 {#equality}

:::compare == 和 is
```python
a = [1, 2]
b = [1, 2]
print(a == b)         # => True
print(a is b)         # => False

x = None
print(x is None)      # => True
print((1, 2) < (1, 3))   # => True
```
```java
var a = List.of(1, 2);
var b = new ArrayList<>(a);
System.out.println(a.equals(b));  // => true
System.out.println(a == b);       // => false
```
```kotlin
val a = listOf(1, 2)
val b = a.toMutableList()
println(a == b)        // => true
println(a === b)       // => false
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 比较内容 | `==` | `equals()` | `==` |
| 比较身份 | `is` | `==` | `===` |
| 判断空值 | `x is None` | `x == null` | `x == null` |
| 序列比大小 | `(1, 2) < (1, 3)` | 不支持 | 不支持 |

> 要点: 自定义类的 `==` 由 `__eq__` 决定，对应 `equals`。元组和列表按字典序逐个比较元素。不同类型比大小会抛 `TypeError`，比如 `1 < "2"`。
:::

:::recap
- 四种内置容器都有字面量：`[]`、`()`、`{}`、`{"k": v}`
- 推导式替代 `map` + `filter`，是最重要的 Python 惯用法
- 函数返回多个值就是返回元组，用解包接收
- `d["x"]` 取不到会抛异常，`d.get("x", 默认值)` 更安全
- 队列用 `deque`，计数用 `Counter`
- `==` 比内容，`is` 比身份，判断 `None` 用 `is`
:::
