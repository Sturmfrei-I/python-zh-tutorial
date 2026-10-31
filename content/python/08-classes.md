---
id: classes
part: 对象、异常与文件
title: 类
lede: 方法要显式写 self，字段不用声明，没有访问修饰符。dataclass 和生成器是最值得掌握的两个工具。
source: 类 | classes.html
seo_title: Python 面向对象：类、继承和 dataclass，对比 Java
seo_description: 讲解 Python 类的 self、__init__、继承、@property、特殊方法、dataclass、枚举和生成器，并和 Java、Kotlin 的类、record、data class 逐项对比。
---

## 定义类 {#class}

`__init__` 是构造函数，`self` 就是 `this`，但必须写在参数列表第一位。创建对象不用 `new`。

:::compare 类和实例
```python
class Dog:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return f"{self.name}: 汪"

d = Dog("Rex")
print(d.speak())  # => Rex: 汪
print(d.name)     # => Rex
```
```java
class Dog {
    private final String name;

    Dog(String name) {
        this.name = name;
    }

    String speak() {
        return name + ": 汪";
    }
}

var d = new Dog("Rex");
System.out.println(d.speak());  // => Rex: 汪
```
```kotlin
class Dog(val name: String) {
    fun speak() = "$name: 汪"
}

val d = Dog("Rex")
println(d.speak())  // => Rex: 汪
println(d.name)     // => Rex
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 构造函数 | `__init__` | 和类同名 | 主构造函数 |
| 当前对象 | `self`，必须写在参数里 | `this`，隐式 | `this`，隐式 |
| 访问成员 | 必须写 `self.` | 可以省略 `this.` | 可以省略 `this.` |
| 字段声明 | 不用声明，赋值时创建 | 必须声明 | 必须声明 |
| 创建对象 | 不用 `new` | 必须写 `new` | = |

> 要点: 忘记写 `self` 是最常见的错误，`def speak():` 调用时会报参数个数不对。
:::

## 类变量和实例变量 {#class-vars}

写在类体里的变量属于类本身，所有实例共享，相当于 `static` 字段。写在 `self` 上的才属于实例。

:::compare 类级成员
```python
class Dog:
    count = 0                # 类变量

    def __init__(self, name):
        self.name = name     # 实例变量
        Dog.count += 1

    @classmethod
    def total(cls):
        return cls.count

    @staticmethod
    def is_adult(age):
        return age >= 2

Dog("Rex")
Dog("Max")
print(Dog.total())      # => 2
print(Dog.is_adult(3))  # => True
```
```java
class Dog {
    static int count = 0;
    final String name;

    Dog(String name) {
        this.name = name;
        count++;
    }

    static int total() {
        return count;
    }
}

new Dog("Rex");
new Dog("Max");
System.out.println(Dog.total());  // => 2
```
```kotlin
class Dog(val name: String) {
    init { count++ }

    companion object {
        var count = 0
        fun total() = count
    }
}

Dog("Rex")
Dog("Max")
println(Dog.total())  // => 2
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 类变量 | 写在类体里 | `static` 字段 | `companion object` 里的属性 |
| 类方法 | `@classmethod`，可被子类覆盖 | `static` 方法，不能覆盖 | `companion object` 里的函数 |
| 静态方法 | `@staticmethod` | `static` 方法 | 顶层函数 |
| 共享范围 | 所有实例共享 | = | = |

> 要点: 别把列表这样的可变对象写成类变量，否则所有实例共用一份，这和可变默认参数是同一类错误。
:::

通过实例赋值 `d.count = 5` 不会修改类变量，而是在实例上新建一个同名属性，把类变量遮住。要改类变量就写 `Dog.count = 5`。

## 继承 {#inherit}

类名后的括号里写父类。所有方法默认都可以被覆盖，不需要 `open`，也不需要 `override` 关键字。

:::compare 继承和方法覆盖
```python
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        raise NotImplementedError

class Cat(Animal):
    def __init__(self, name, lives=9):
        super().__init__(name)
        self.lives = lives

    def speak(self):
        return f"{self.name}: 喵"

c = Cat("Tom")
print(c.speak())              # => Tom: 喵
print(isinstance(c, Animal))  # => True
```
```java
abstract class Animal {
    final String name;
    Animal(String name) { this.name = name; }
    abstract String speak();
}

class Cat extends Animal {
    Cat(String name) { super(name); }

    @Override
    String speak() { return name + ": 喵"; }
}

Animal c = new Cat("Tom");
System.out.println(c.speak());  // => Tom: 喵
System.out.println(c instanceof Animal);  // => true
```
```kotlin
abstract class Animal(val name: String) {
    abstract fun speak(): String
}

class Cat(name: String) : Animal(name) {
    override fun speak() = "$name: 喵"
}

val c: Animal = Cat("Tom")
println(c.speak())     // => Tom: 喵
println(c is Animal)   // => true
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 语法 | `class Cat(Animal):` | `class Cat extends Animal` | `class Cat : Animal()` |
| 能否被继承 | 默认可以 | 默认可以 | 默认不行，要标 `open` |
| 覆盖方法 | 直接重写 | `@Override` 可选 | 必须写 `override` |
| 调用父类构造 | `super().__init__()` | `super()` | 写在类头 |
| 抽象类 | `abc.ABC` + `@abstractmethod` | `abstract` | `abstract` |
| 类型判断 | `isinstance(c, Animal)` | `c instanceof Animal` | `c is Animal` |
| 多态 | 按实际类型调用方法 | = | = |

> 要点: 方法覆盖时可以加 `typing.override`（3.12 新增），让类型检查器帮忙核对。
:::

Python 没有 `interface` 关键字。只要对象有需要的方法就能用，这叫鸭子类型。想让类型检查器验证，就用 `typing.Protocol`，实现类不需要显式声明继承关系。

:::compare 接口的替代方式
```python
from typing import Protocol

class Greeter(Protocol):
    def greet(self) -> str: ...

class En:           # 没有写继承关系
    def greet(self) -> str:
        return "Hello"

def run(g: Greeter):
    print(g.greet())

run(En())           # => Hello
```
```java
interface Greeter {
    String greet();
}

class En implements Greeter {
    public String greet() { return "Hello"; }
}

static void run(Greeter g) {
    System.out.println(g.greet());
}

run(new En());  // => Hello
```
```kotlin
interface Greeter {
    fun greet(): String
}

class En : Greeter {
    override fun greet() = "Hello"
}

fun run(g: Greeter) = println(g.greet())

run(En())  // => Hello
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 定义接口 | `Protocol` 或鸭子类型 | `interface` | `interface` |
| 声明实现 | 不需要 | `implements` | `: Greeter` |
| 检查时机 | 类型检查工具，运行时不查 | 编译时 | 编译时 |
| 调用方依赖 | 只依赖方法，不依赖具体类 | = | = |

> 要点: 小型项目直接靠鸭子类型就够了。大型项目用 `Protocol` 或 `ABC` 把约定写明。
:::

:::more 多重继承和 MRO
Python 支持多重继承：`class Duck(Swimmer, Walker): ...`。方法按 MRO（方法解析顺序）查找，可以用 `Duck.__mro__` 查看。`super()` 也沿着 MRO 走，而不只是找直接父类。实际项目主要用它写 Mixin，给类附加一组方法，用途接近 Java 的默认接口方法。

```python
class Swimmer:
    def move(self):
        return "游"

class Walker:
    def move(self):
        return "走"

class Duck(Swimmer, Walker):
    pass

print(Duck().move())  # => 游
print([c.__name__ for c in Duck.__mro__])  # => ['Duck', 'Swimmer', 'Walker', 'object']
```
:::

## 访问控制 {#private}

Python 没有 `private`。单下划线是「内部使用」的约定，双下划线会触发名称改写，用来避免子类意外覆盖。需要受控访问时，用 `@property` 把方法变成属性。

:::compare 私有字段和属性
```python
class Account:
    def __init__(self, balance):
        self._balance = balance

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        if value < 0:
            raise ValueError("余额不能为负")
        self._balance = value

a = Account(100)
a.balance = 50
print(a.balance)  # => 50
```
```java
class Account {
    private int balance;

    Account(int balance) {
        this.balance = balance;
    }

    int getBalance() { return balance; }

    void setBalance(int value) {
        if (value < 0) throw new
            IllegalArgumentException("余额不能为负");
        balance = value;
    }
}

var a = new Account(100);
a.setBalance(50);
System.out.println(a.getBalance());  // => 50
```
```kotlin
class Account(balance: Int) {
    var balance = balance
        set(value) {
            require(value >= 0) { "余额不能为负" }
            field = value
        }
}

val a = Account(100)
a.balance = 50
println(a.balance)  // => 50
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 私有字段 | `_name` 是约定，不强制 | `private` | `private` |
| 访问器 | `@property` | `getXxx()` 方法 | `get()`、`set()` |
| 调用方写法 | `a.balance` | `a.getBalance()` | `a.balance` |
| 何时加校验 | 需要时再改，调用方不用变 | 通常提前写好访问器 | = |

> 要点: 双下划线 `__x` 会触发名称改写，用来避免子类意外覆盖，并不是真正的私有。
:::

## 特殊方法 {#dunder}

双下划线包围的方法由解释器在特定语法下自动调用。实现它们就能让自定义类支持 `print`、`==`、`+`、`len()`、`for` 等语法。

:::map 特殊方法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `__str__` | `toString()` | `toString()` | `print` 和 `str()` 时调用 |
| `__repr__` | 无 | 无 | 调试用的字符串，交互模式显示的就是它 |
| `__eq__` | `equals()` | `equals()` | `==` 时调用 |
| `__hash__` | `hashCode()` | `hashCode()` | 重写 `__eq__` 时要一起处理 |
| `__lt__` | `compareTo()` | `compareTo()` | `<` 时调用，用于排序 |
| `__add__` | 无 | `operator fun plus` | `+` 时调用 |
| `__len__` | `size()` | `size` | `len()` 时调用 |
| `__getitem__` | `get(i)` | `operator fun get` | `obj[i]` 时调用 |
| `__iter__` | `iterator()` | `operator fun iterator` | `for` 循环时调用 |
| `__call__` | 函数式接口 | `operator fun invoke` | 让对象能像函数一样调用 |
| `__enter__` / `__exit__` | `AutoCloseable` | `Closeable` | `with` 时调用 |
:::

:::more 运行时查看和修改对象
下面这些内置函数相当于 Java 的反射，用起来简单得多。

```python
class User:
    def __init__(self, name):
        self.name = name

u = User("Ann")
print(type(u).__name__)          # => User
print(hasattr(u, "name"))        # => True
print(getattr(u, "age", 0))      # => 0
setattr(u, "age", 30)
print(u.__dict__)                # => {'name': 'Ann', 'age': 30}
print(issubclass(User, object))  # => True
```

`obj.method` 不加括号时得到绑定方法，可以存起来稍后调用。`eval` 和 `exec` 能执行字符串形式的代码，不要用在外部输入上。
:::

## dataclass {#dataclass}

只保存数据的类用 `dataclass`，自动生成 `__init__`、`__repr__` 和 `__eq__`。这是日常写类最常用的方式。

:::compare 数据类
```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int = 0

p = Point(3)
print(p)              # => Point(x=3, y=0)
print(p == Point(3))  # => True
```
```java
record Point(int x, int y) {
    Point(int x) { this(x, 0); }
}

var p = new Point(3);
System.out.println(p);  // => Point[x=3, y=0]
System.out.println(p.equals(new Point(3)));  // => true
```
```kotlin
data class Point(val x: Int, val y: Int = 0)

val p = Point(3)
println(p)              // => Point(x=3, y=0)
println(p == Point(3))  // => true
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 语法 | `@dataclass` | `record` | `data class` |
| 可变性 | 默认可变，`frozen=True` 后不可变 | 不可变 | 由 `val`、`var` 决定 |
| 字段默认值 | `y: int = 0` | 要写额外的构造函数 | `y: Int = 0` |
| 复制并修改 | `dataclasses.replace(p, x=1)` | 手写 | `p.copy(x = 1)` |
| 自动生成 | 构造函数、相等比较、字符串表示 | = | = |

> 要点: 类型注解在这里是必须写的，dataclass 靠它识别字段。
:::

## 枚举 {#enums}

枚举要继承 `enum.Enum`。成员写成类变量，每个成员都有 `name` 和 `value`。

:::compare 枚举
```python
from enum import Enum

class Color(Enum):
    RED = "红"
    GREEN = "绿"

c = Color.RED
print(c.name, c.value)  # => RED 红
print(Color("绿"))      # => Color.GREEN
print(c is Color.RED)   # => True
print(len(Color))       # => 2
```
```java
enum Color {
    RED("红"), GREEN("绿");

    final String label;

    Color(String label) { this.label = label; }
}

var c = Color.RED;
System.out.println(c.name() + " " + c.label);  // => RED 红
System.out.println(c == Color.RED);  // => true
```
```kotlin
enum class Color(val label: String) {
    RED("红"), GREEN("绿")
}

val c = Color.RED
println("${c.name} ${c.label}")  // => RED 红
println(c == Color.RED)          // => true
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 定义 | 继承 `Enum` | `enum` 关键字 | `enum class` |
| 附带的值 | `value`，一个成员一个值 | 构造函数，可以有多个字段 | 构造函数，可以有多个字段 |
| 按值查找 | `Color("绿")` | 手写 | 手写 |
| 按名查找 | `Color["RED"]` | `Color.valueOf("RED")` | `Color.valueOf("RED")` |
| 比较 | 用 `is` | 用 `==` | 用 `==` |
| 成员是单例 | 每个成员只有一个实例 | = | = |

> 要点: 值不重要时用 `enum.auto()` 自动编号。`match` 里比较枚举要写 `case Color.RED:`。
:::

## 迭代器和生成器 {#generators}

`for` 循环依靠迭代器协议：先用 `iter(obj)` 取得迭代器，再不断调用 `next()`，取完时抛 `StopIteration`。自己写迭代器很少见，生成器函数更简单。函数体里有 `yield` 时，调用它会得到一个惰性序列。

:::compare 生成器
```python
def countdown(n):
    while n > 0:
        yield n
        n -= 1

print(list(countdown(3)))  # => [3, 2, 1]

for x in countdown(2):
    print(x)               # 2 1

squares = (x * x for x in range(4))
print(sum(squares))        # => 14
```
```java
var list = Stream
    .iterate(3, n -> n > 0, n -> n - 1)
    .toList();
System.out.println(list);  // => [3, 2, 1]

var total = IntStream.range(0, 4)
    .map(x -> x * x).sum();
System.out.println(total);  // => 14
```
```kotlin
fun countdown(n: Int) = sequence {
    var i = n
    while (i > 0) {
        yield(i)
        i--
    }
}

println(countdown(3).toList())  // => [3, 2, 1]

val total = (0 until 4).asSequence()
    .map { it * it }.sum()
println(total)  // => 14
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 定义方式 | 函数里写 `yield` | `Stream.iterate` 或手写 `Iterator` | `sequence { yield(x) }` |
| 惰性推导 | `(x * x for x in xs)` | `stream().map()` | `asSequence().map {}` |
| 重复遍历 | 只能遍历一次 | 只能遍历一次 | 通常可以重复遍历 |
| 求值时机 | 用到时才计算 | = | = |

> 要点: 生成器不占内存，适合处理大数据或无限序列。需要重复使用时，用 `list()` 转成列表。
:::


:::more 自己写迭代器
实现 `__iter__` 和 `__next__` 就能用于 `for`，对应 Java 的 `Iterable` 和 `Iterator`。大多数情况下用生成器更简单。

```python
class Countdown:
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.current == 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1

print(list(Countdown(3)))  # => [3, 2, 1]
```
:::

:::recap
- `self` 必须显式写，`__init__` 是构造函数，字段在里面赋值时创建
- 类体里的变量是类变量，相当于 `static`
- 没有 `interface` 和 `private`，靠鸭子类型和下划线约定
- `@property` 让字段和访问器的调用方式相同，所以不用提前写 getter
- 数据类用 `@dataclass`，`frozen=True` 对应 Java 的 `record`
- 特殊方法让自定义类支持内置语法
- 枚举继承 `Enum`，每个成员有 `name` 和 `value`
- 生成器函数用 `yield` 写惰性序列，对应 Kotlin 的 `sequence`
:::
