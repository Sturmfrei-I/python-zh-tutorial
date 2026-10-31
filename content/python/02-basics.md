---
id: variables-and-types
part: 语言基础
title: 变量与基础类型
lede: 四种最常用的基础类型。重点看整除、切片和字符串格式化，这些地方最容易带着旧习惯写错。
source: Python 速览 | introduction.html ; 浮点算术 | floatingpoint.html
seo_title: Python 基础语法：变量、字符串和列表，对比 Java
seo_description: 讲解 Python 变量、整除与浮点数精度、字符串切片、f-string 和列表，并和 Java、Kotlin 逐项对比，帮你避开转 Python 时最容易犯的错误。
---

## 变量 {#vars}

赋值就是把名字绑定到对象上。不用声明类型，也没有 `val` 和 `final`。

:::compare 声明变量
```python
name = "Ada"
age = 36
age = "三十六"    # 合法：可以改绑到别的类型
MAX_SIZE = 100    # 全大写只是约定
```
```java
String name = "Ada";
var age = 36;
// age = "三十六";  编译错误
final int MAX_SIZE = 100;
```
```kotlin
val name = "Ada"
var age = 36
// age = "三十六"  编译错误
val MAX_SIZE = 100
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 类型声明 | 不写，类型跟着值走 | 写类型，或用 `var` 推断（Java 10 起） | 自动推断，也可以显式写 |
| 改变类型 | 可以改绑到别的类型 | 编译错误 | 编译错误 |
| 只读变量 | 没有语法支持 | `final` | `val` |
| 常量 | 全大写，只是约定 | `static final` | `const val` |
| 对象赋值 | 传递对象引用 | = | = |

> java: `var` 只能用于有初始值的局部变量，字段、方法参数和返回类型都要写明类型。Kotlin 的 `var` 表示可变，Java 的 `var` 只负责推断类型，只读仍然靠 `final`，`final var` 才相当于 Kotlin 的 `val`。
> 要点: Python 的类型错误不会被编译器提前拦下，所以测试和类型检查工具更重要。
:::

Python 是动态类型，但类型转换很严格，不会悄悄把数字变成字符串。这一点和 Java、Kotlin 的 `+` 不一样。

:::compare 字符串拼接数字
```python
print("年龄：" + str(36))  # => 年龄：36
print(f"年龄：{36}")       # => 年龄：36
# "年龄：" + 36  抛出 TypeError
```
```java
System.out.println("年龄：" + 36);  // => 年龄：36
```
```kotlin
println("年龄：" + 36)  // => 年龄：36
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| `"a" + 1` | 抛 `TypeError` | 得到 `"a1"` | 得到 `"a1"` |
| 数字转字符串 | 必须显式转换 | 自动转换 | 自动转换 |
| 常用写法 | f-string | `+` 拼接 | 字符串模板 |

> 要点: Python 是动态类型，但不做隐式转换。日常拼接都用 f-string，它会自动转换。
:::

没有值时用 `None`，对应 `null`。判断时写 `x is None`，不写 `x == None`。Python 没有 Kotlin 的空安全，访问 `None` 的属性会在运行时抛 `AttributeError`。

## 数字 {#numbers}

常用的数字类型只有 `int` 和 `float`。`int` 没有大小上限，`float` 就是 64 位双精度。

:::compare 除法和大整数
```python
print(7 / 2)     # => 3.5
print(7 // 2)    # => 3
print(-7 // 2)   # => -4
print(-7 % 3)    # => 2
print(2 ** 100)  # => 1267650600228229401496703205376
```
```java
System.out.println(7 / 2);    // => 3
System.out.println(7 / 2.0);  // => 3.5
System.out.println(-7 / 2);   // => -3
System.out.println(-7 % 3);   // => -1
var big = BigInteger.TWO.pow(100);
```
```kotlin
println(7 / 2)        // => 3
println(7 / 2.0)      // => 3.5
println(-7 / 2)       // => -3
println((-7).mod(3))  // => 2
val big = 2.toBigInteger().pow(100)
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 整数相除 | `/` 得到浮点数 | `/` 截断为整数 | `/` 截断为整数 |
| 向下取整 | `//` | `Math.floorDiv` | `floorDiv` |
| `-7 % 3` | 2 | -1 | -1，`mod` 才得到 2 |
| 整数上限 | 没有上限 | `long` 有上限，超出用 `BigInteger` | `Long` 有上限，超出用 `BigInteger` |
| 运算优先级 | 先乘除后加减 | = | = |

> 要点: 迁移时最容易写错的是 `/`。需要整数结果时一定写 `//`。
:::

Python 没有 `++` 和 `--`，写 `n += 1`。乘方的优先级比负号高，`-3 ** 2` 是 -9，想要 9 就写 `(-3) ** 2`。`complex` 复数类型很少用到，知道有就行。

:::map 数字类型
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `int` | `int` / `long` / `BigInteger` | `Int` / `Long` / `BigInteger` | Python 只有一种，自动扩容 |
| `float` | `double` | `Double` | Python 没有 32 位 float |
| `True` / `False` | `true` / `false` | `true` / `false` | 首字母大写 |
| `None` | `null` | `null` | 判断时用 `is None` |
| `x ** y` | `Math.pow(x, y)` | `x.pow(y)` | 整数的非负整数次幂仍是整数 |
| `abs(x)`、`round(x, 2)` | `Math.abs(x)` | `abs(x)` | 内置函数，不用导入 |
:::

### 浮点数的精度

`float` 是 IEEE 754 双精度浮点数。十进制的 0.1 在二进制里是无限循环小数，只能存近似值，所以比较时不能直接用 `==`。金额计算要用第 10 章的 `Decimal`。

:::compare 浮点比较和舍入
```python
import math

print(0.1 + 0.2)  # => 0.30000000000000004
print(0.1 + 0.2 == 0.3)  # => False
print(math.isclose(0.1 + 0.2, 0.3))  # => True

print(round(2.5))  # => 2
print(round(3.5))  # => 4
```
```java
System.out.println(0.1 + 0.2);  // => 0.30000000000000004
System.out.println(0.1 + 0.2 == 0.3);  // => false
System.out.println(
    Math.abs(0.1 + 0.2 - 0.3) < 1e-9);  // => true

System.out.println(Math.round(2.5));  // => 3
System.out.println(Math.round(3.5));  // => 4
```
```kotlin
import kotlin.math.abs
import kotlin.math.roundToInt

println(0.1 + 0.2)  // => 0.30000000000000004
println(0.1 + 0.2 == 0.3)  // => false
println(abs(0.1 + 0.2 - 0.3) < 1e-9)  // => true

println(2.5.roundToInt())  // => 3
println(3.5.roundToInt())  // => 4
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 近似比较 | `math.isclose(a, b)` | 手写 `Math.abs(a - b) < eps` | 手写 `abs(a - b) < eps` |
| `2.5` 舍入 | `round` 得 2，银行家舍入 | `Math.round` 得 3 | `roundToInt` 得 3 |
| 浮点标准 | IEEE 754 双精度 | = | = |
| `0.1 + 0.2` | 不等于 `0.3` | = | = |

> 要点: `round()` 恰好在中间时取偶数，处理金额时用 `Decimal` 并显式指定舍入方式。
:::

:::more 查看浮点数的真实值
`(0.1).as_integer_ratio()` 返回精确的分数表示，`(0.1).hex()` 显示十六进制形式。`f"{0.1:.20f}"` 能看到更多位数。`math.fsum()` 能减小累加误差，`fractions.Fraction` 可以做精确的分数运算。
:::

## 字符串 {#strings}

单引号和双引号完全等价。字符串不可变，这一点三门语言相同。Python 没有 `char` 类型，单个字符就是长度为 1 的字符串。

:::compare 索引和切片
```python
s = "Python"
print(s[0])     # => P
print(s[-1])    # => n
print(s[0:2])   # => Py
print(s[2:])    # => thon
print(s[::-1])  # => nohtyP
print(len(s))   # => 6
print("ab" * 2) # => abab
```
```java
var s = "Python";
var n = s.length();
System.out.println(s.charAt(0));      // => P
System.out.println(s.charAt(n - 1));  // => n
System.out.println(s.substring(0, 2));// => Py
System.out.println(s.substring(2));   // => thon
var r = new StringBuilder(s).reverse();
System.out.println(r);                // => nohtyP
System.out.println("ab".repeat(2));   // => abab
```
```kotlin
val s = "Python"
println(s[0])              // => P
println(s.last())          // => n
println(s.substring(0, 2)) // => Py
println(s.drop(2))         // => thon
println(s.reversed())      // => nohtyP
println(s.length)          // => 6
println("ab".repeat(2))    // => abab
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 单个字符 | 长度为 1 的字符串 | `char` 类型 | `Char` 类型 |
| 负数下标 | 支持，`s[-1]` 是最后一个 | 不支持 | 不支持，用 `last()` |
| 取子串 | `s[0:2]` | `s.substring(0, 2)` | `s.substring(0, 2)` |
| 范围越界 | 切片不报错 | 抛异常 | 抛异常 |
| 字符串长度 | `len(s)` | `s.length()` | `s.length` |
| 不可变性 | 字符串不可变 | = | = |
| 区间规则 | 左闭右开 | = | = |

> 要点: 切片同样适用于列表和元组，是 Python 最常用的语法之一。
:::

:::compare 字面量的三种写法
```python
name = "Ada"
print(f"Hi, {name}!")  # => Hi, Ada!
print(r"C:\new")       # => C:\new
text = """第一行
第二行"""
print(len(text))       # => 7
```
```java
var name = "Ada";
System.out.println("Hi, " + name + "!");  // => Hi, Ada!
System.out.println("C:\\new");  // => C:\new
var text = """
    第一行
    第二行""";
System.out.println(text.length());  // => 7
```
```kotlin
val name = "Ada"
println("Hi, $name!")   // => Hi, Ada!
println("""C:\new""")   // => C:\new
val text = """
    第一行
    第二行""".trimIndent()
println(text.length)    // => 7
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 插值 | `f"{name}"` | 没有内置语法，用 `+` 或 `format` | `"$name"` |
| 原始字符串 | `r"..."` | 不支持 | `"""..."""` |
| 多行字符串 | `"""` 原样保留缩进 | `"""` 自动去除公共缩进 | `"""` 配合 `trimIndent()` |
| 引号 | 单双引号等价 | 字符串只能用双引号 | 字符串只能用双引号 |

> 要点: 前缀可以组合，比如 `rf"..."`。日常最常用的是 f-string。
:::

转义字符的写法和大多数语言相同，比如 `\n` 和 `\\`。相邻的字符串字面量会自动拼接，长字符串常这样分行写。

```python
message = ("第一段，"
           "第二段")
print(message)  # => 第一段，第二段
```

:::map 常用字符串方法
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `s.strip()` | `s.strip()` | `s.trim()` | |
| `s.split(",")` | `s.split(",")` | `s.split(",")` | Java 返回数组，其余返回列表 |
| `",".join(xs)` | `String.join(",", xs)` | `xs.joinToString(",")` | Python 把方法放在分隔符上 |
| `s.replace("a", "b")` | `s.replace("a", "b")` | `s.replace("a", "b")` | |
| `s.startswith("a")` | `s.startsWith("a")` | `s.startsWith("a")` | Python 全小写 |
| `s.upper()` | `s.toUpperCase()` | `s.uppercase()` | |
| `"a" in s` | `s.contains("a")` | `"a" in s` | |
| `s.find("a")` | `s.indexOf("a")` | `s.indexOf("a")` | 找不到都返回 -1 |
| `int("42")` | `Integer.parseInt("42")` | `"42".toInt()` | |
| `str(42)` | `String.valueOf(42)` | `42.toString()` | |
| `ord("a")`、`chr(97)` | `(int) 'a'`、`(char) 97` | `'a'.code`、`97.toChar()` | 字符和码点互转 |
:::

## 列表 {#lists}

`list` 是 Python 最常用的容器，相当于 `ArrayList`。用方括号写字面量，元素类型可以混合。

:::compare 列表基础
```python
nums = [1, 2, 3]
nums.append(4)
nums[0] = 10
print(nums[1:3])   # => [2, 3]
print(nums + [5])  # => [10, 2, 3, 4, 5]
print(len(nums))   # => 4
print(3 in nums)   # => True
```
```java
var nums = new ArrayList<>(List.of(1, 2, 3));
nums.add(4);
nums.set(0, 10);
System.out.println(nums.subList(1, 3));  // => [2, 3]
System.out.println(nums.size());         // => 4
System.out.println(nums.contains(3));    // => true
```
```kotlin
val nums = mutableListOf(1, 2, 3)
nums.add(4)
nums[0] = 10
println(nums.slice(1..2))  // => [2, 3]
println(nums + 5)          // => [10, 2, 3, 4, 5]
println(nums.size)         // => 4
println(3 in nums)         // => true
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 可变性 | 始终可变 | `ArrayList` 可变，`List.of` 不可变 | `mutableListOf` 可变，`listOf` 只读 |
| 字面量 | `[1, 2, 3]` | 没有，用 `List.of` | 没有，用 `listOf` |
| 元素类型 | 可以混合 | 由泛型限定 | 由泛型限定 |
| 取片段 | 切片返回新列表 | `subList` 返回视图 | `slice` 返回新列表 |
| 底层结构 | 动态数组 | = | = |
| 赋值 | 共享同一个对象 | = | = |

> 要点: 长度统一用内置函数 `len()`，不是方法或属性。
:::

切片还能写在赋值左边，用来批量替换元素，长度可以不同：`nums[1:3] = [7, 8, 9]`。`nums[:] = []` 会清空列表。

:::tip 赋值共享同一个对象
`b = a` 不会复制列表，两个名字指向同一个对象。要复制时写 `a.copy()` 或 `a[:]`，它们都是浅拷贝，内层对象仍然共享。需要完全独立的副本时用 `copy.deepcopy(a)`。同样的道理，`[[0] * 3] * 2` 里的两行是同一个列表，创建二维列表要写 `[[0] * 3 for _ in range(2)]`。
:::

## 第一段小程序 {#first-program}

下面用斐波那契数列把前面的内容串起来。`while` 和其他语言一样，条件为真时循环。

:::compare 多重赋值
```python
a, b = 0, 1
while a < 30:
    print(a, end=" ")
    a, b = b, a + b
```
```java
int a = 0, b = 1;
while (a < 30) {
    System.out.print(a + " ");
    int next = a + b;
    a = b;
    b = next;
}
```
```kotlin
var a = 0
var b = 1
while (a < 30) {
    print("$a ")
    val next = a + b
    a = b
    b = next
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 交换变量 | `a, b = b, a` | 需要临时变量 | 需要临时变量 |
| 同时赋值 | 右边先全部求值，再一起赋值 | 逐条执行 | 逐条执行 |
| 输出不换行 | `print(a, end=" ")` | `System.out.print(a)` | `print(a)` |
| `while` | 条件为真时循环 | = | = |

> 要点: `print` 默认在末尾换行。`end=" "` 改成空格结尾，`sep=", "` 改变多个参数之间的分隔符。
:::

:::recap
- 赋值是绑定名字，变量没有类型，也没有语法层面的常量
- `/` 得到浮点数，`//` 向下取整，`int` 没有上限
- 浮点数不能用 `==` 比较，改用 `math.isclose`，`round()` 恰好在中间时取偶数
- 字符串和列表都支持 `[起:止:步长]` 切片，区间左闭右开
- 用 f-string 拼接文本，`+` 不会自动把数字转成字符串
- 长度统一用 `len()`，成员判断统一用 `in`
:::
