---
id: modules
part: 函数与数据
title: 模块与包
lede: 一个 .py 文件就是一个模块，一个目录就是一个包。import 会真的执行代码，这点和 Java 不同。
source: 模块 | modules.html
seo_title: Python 模块与包：import、__name__ 和相对导入，对比 Java package
seo_description: 讲解 Python 的 import 机制、__name__ 的作用、模块搜索路径、包和相对导入，并对比 Java、Kotlin 的 package 和类路径。
---

## 模块和 import {#import}

每个 `.py` 文件都是一个模块，模块名就是文件名。导入后，模块里的函数、类和变量都可以通过模块名访问。

:::compare 导入
```python
import math
from math import sqrt, pi
from datetime import date as Day

print(math.floor(2.7))   # => 2
print(sqrt(16))          # => 4.0
print(Day(2026, 1, 1))   # => 2026-01-01
```
```java
import java.time.LocalDate;
import static java.lang.Math.sqrt;

System.out.println(Math.floor(2.7));  // => 2.0
System.out.println(sqrt(16));         // => 4.0
System.out.println(
    LocalDate.of(2026, 1, 1));  // => 2026-01-01
```
```kotlin
import kotlin.math.floor
import kotlin.math.sqrt
import java.time.LocalDate as Day

println(floor(2.7))        // => 2.0
println(sqrt(16.0))        // => 4.0
println(Day.of(2026, 1, 1))  // => 2026-01-01
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 发生时机 | 运行时执行模块代码 | 编译期的名字简写 | 编译期的名字简写 |
| 导入单位 | 模块，也就是文件 | 类 | 类、函数或属性 |
| 别名 | `import x as y` | 不支持 | = |
| 导入函数 | `from math import sqrt` | `import static` | `import kotlin.math.sqrt` |

> 要点: 模块顶层不要写耗时操作或副作用。不要用 `from x import *`，来源不清楚，还容易覆盖名字。
:::

## 脚本入口 {#entry-point}

模块被直接运行时，`__name__` 的值是 `"__main__"`。被别的文件导入时，`__name__` 是模块名。用它就能让文件既能当脚本运行，又能被导入而不触发运行逻辑。

:::compare main 入口
```python
def main():
    print("运行中")   # => 运行中

if __name__ == "__main__":
    main()
```
```java
public class App {
    public static void main(String[] args) {
        System.out.println("运行中");
    }
}
```
```kotlin
fun main() {
    println("运行中")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 入口写法 | `if __name__ == "__main__":` | `public static void main` | `fun main()` |
| 是否必须 | 可选 | 必须 | 必须 |
| 被其他文件引用时 | 顶层代码会执行，这个分支不会 | 入口不执行 | 入口不执行 |

> 要点: 把逻辑放进 `main()` 函数，只在底部调用，这样其他模块和测试都能安全地导入这个文件。
:::

## 模块搜索路径 {#path}

`import` 按 `sys.path` 里的目录依次查找，相当于类路径。顺序是脚本所在目录、`PYTHONPATH` 环境变量、标准库、`site-packages`（第三方包）。

:::warn 别和标准库重名
因为脚本所在目录排在最前面，自己写一个 `random.py` 或 `json.py` 会遮盖标准库，其他代码 `import random` 时就会拿到你的文件，报出很奇怪的错误。
:::

:::more __pycache__、dir() 和标准模块
Python 把编译好的字节码缓存在 `__pycache__/模块名.cpython-312.pyc`，源文件改动后自动更新，这个目录应该写进 `.gitignore`。内置函数 `dir(模块)` 列出模块里的所有名字，在交互模式下查 API 很方便。`help(模块)` 显示文档。

在交互模式下改了模块后，再次 `import` 不会生效，要调用 `importlib.reload(模块)`。包的 `__path__` 属性决定到哪些目录里找子模块，很少需要改动。
:::

## 包 {#packages}

包是包含模块的目录，通常放一个 `__init__.py`。这个文件在包第一次导入时执行，可以是空文件，也可以用来导出公开 API。

```text
shop/
├── __init__.py
├── utils.py
└── orders/
    ├── __init__.py
    └── service.py
```

:::compare 包和导入路径
```python no-run
# shop/orders/service.py
from shop.utils import money    # 绝对导入
from ..utils import money       # 相对导入

# shop/__init__.py，导出公开 API
from .orders.service import place_order
__all__ = ["place_order"]
```
```java no-run
// shop/orders/Service.java
package shop.orders;

import shop.utils.Money;

public class Service {
    public void placeOrder() { }
}
```
```kotlin no-run
// shop/orders/Service.kt
package shop.orders

import shop.utils.money

fun placeOrder() { }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 包名来源 | 目录结构 | `package` 语句 | `package` 语句 |
| 目录要求 | 目录就是包 | 必须和 `package` 一致 | 可以不一致 |
| 相对导入 | `from ..utils import x` | 不支持 | 不支持 |
| 可见性 | 默认公开，`_name` 是约定 | 访问修饰符 | 访问修饰符 |
| 包初始化 | `__init__.py` | 没有 | 没有 |

> 要点: 公开 API 通常在 `__init__.py` 里集中导出，`__all__` 决定 `import *` 导出什么。
:::

:::warn 用了相对导入的文件要用 -m 运行
直接执行 `python3 shop/orders/service.py` 会报 `ImportError`，因为被直接运行的文件 `__name__` 是 `"__main__"`，它不知道自己属于哪个包。要在项目根目录执行 `python3 -m shop.orders.service`。
:::

:::map 模块系统对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| 模块（`.py` 文件） | 类文件 | 文件 | Python 的最小导入单位是文件 |
| 包（目录） | `package` | `package` | |
| `sys.path` | classpath | classpath | |
| `__init__.py` | 无 | 无 | 包初始化代码 |
| `__all__` | `public` | `public` / `internal` | Python 里只影响 `import *` |
| `_name` | `private` / 包私有 | `private` / `internal` | 约定，不强制 |
:::

:::recap
- 文件即模块，目录即包，包名由目录结构决定
- `import` 在运行时执行模块顶层代码，只执行一次
- 脚本入口统一写 `if __name__ == "__main__":`
- 别用 `from x import *`，别和标准库模块重名
- `__init__.py` 负责包初始化和导出公开 API
:::
