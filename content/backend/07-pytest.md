---
id: pytest
part: 测试与部署
title: pytest 测试
lede: 测试函数就是普通函数，断言就是 assert。没有测试类，也没有一长串 assertEquals，用过 JUnit 的话半小时就能上手。
source: pytest 文档 | https://docs.pytest.org/en/stable/ ; fixture | https://docs.pytest.org/en/stable/how-to/fixtures.html ; 参数化 | https://docs.pytest.org/en/stable/how-to/parametrize.html ; monkeypatch | https://docs.pytest.org/en/stable/how-to/monkeypatch.html ; pytest-asyncio | https://pytest-asyncio.readthedocs.io/en/stable/ ; unittest.mock | https://docs.python.org/zh-cn/3.12/library/unittest.mock.html
versions: pytest 9.2 · pytest-asyncio 1.4 · JUnit 6
seo_title: pytest 教程：断言、fixture 和 mock，对比 JUnit
seo_description: pytest 入门：测试发现、断言、fixture、参数化、monkeypatch、mock、异步测试和 FastAPI 接口测试，并和 JUnit、Mockito、MockK 对比。
---

## 第一个测试 {#first}

pytest 自动找到 `test_*.py` 文件里以 `test_` 开头的函数并运行。断言直接写 `assert`，失败时 pytest 会显示表达式两边的实际值。

```bash
pip install pytest
pytest          # 运行全部测试
pytest -x       # 遇到第一个失败就停止
pytest -k add   # 只运行名字里带 add 的测试
pytest --lf     # 只重新运行上次失败的测试
```

:::compare 写一个测试
```python
def add(a: int, b: int) -> int:
    return a + b

def test_add():
    assert add(1, 2) == 3

def test_list():
    assert [1, 2] + [3] == [1, 2, 3]
§ if __name__ == "__main__":
§     import pytest
§     assert pytest.main(["-q", "-p", "no:cacheprovider", "snippet.py"]) == 0
```
```java no-run
class CalculatorTest {
    @Test
    void add() {
        assertEquals(3, Calculator.add(1, 2));
    }

    @Test
    void list() {
        assertEquals(List.of(1, 2, 3), Calculator.append(List.of(1, 2), 3));
    }
}
§ static class Calculator {
§     static int add(int a, int b) { return a + b; }
§     static List<Integer> append(List<Integer> list, int value) { return list; }
§ }
```
```kotlin no-run
class CalculatorTest {
    @Test
    fun add() {
        assertEquals(3, 1 + 2)
    }

    @Test
    fun list() {
        assertEquals(listOf(1, 2, 3), listOf(1, 2) + 3)
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 发现测试 | 函数名以 `test_` 开头 | `@Test` 注解 | `@Test` 注解 |
| 测试类 | 不需要 | 需要 | 需要 |
| 断言 | `assert` 语句 | `assertEquals` | `assertEquals` |
| 失败信息 | 自动显示两边的值 | 显示期望值和实际值 | 显示期望值和实际值 |

> 要点: 只有测试函数和 `conftest.py` 里的 `assert` 会被 pytest 改写。普通业务代码里的 `assert` 在 `python -O` 时会被去掉，不要用它做校验。
:::

## 断言异常 {#raises}

`pytest.raises` 是一个上下文管理器，代码块里没有抛出指定异常时测试失败。`match` 用正则检查异常信息。

:::compare 断言抛出异常
```python
import pytest

def parse_age(text: str) -> int:
    age = int(text)
    if age < 0:
        raise ValueError("年龄不能为负数")
    return age

def test_negative():
    with pytest.raises(ValueError, match="负数"):
        parse_age("-1")
§ if __name__ == "__main__":
§     assert pytest.main(["-q", "-p", "no:cacheprovider", "snippet.py"]) == 0
```
```java no-run
@Test
void negative() {
    var error = assertThrows(
        IllegalArgumentException.class,
        () -> parseAge("-1"));
    assertTrue(error.getMessage().contains("负数"));
}
§ int parseAge(String text) { return 0; }
```
```kotlin no-run
@Test
fun negative() {
    val error = assertFailsWith<IllegalArgumentException> {
        parseAge("-1")
    }
    assertContains(error.message.orEmpty(), "负数")
}
§ fun parseAge(text: String) = 0
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 写法 | `with pytest.raises()` | `assertThrows` | `assertFailsWith` |
| 检查信息 | `match` 正则 | 取出异常再判断 | 取出异常再判断 |

> 要点: `with pytest.raises(...) as info` 能拿到异常对象，`info.value` 就是它。
:::

## 参数化 {#parametrize}

同一个逻辑要测多组数据时用参数化，每组数据算一个测试，失败时能看到是哪一组。

:::compare 参数化测试
```python
import pytest

def is_even(n: int) -> bool:
    return n % 2 == 0

@pytest.mark.parametrize("value, expected", [
    (2, True),
    (3, False),
    (0, True),
])
def test_is_even(value: int, expected: bool):
    assert is_even(value) == expected
§ if __name__ == "__main__":
§     assert pytest.main(["-q", "-p", "no:cacheprovider", "snippet.py"]) == 0
```
```java no-run
@ParameterizedTest
@CsvSource({"2, true", "3, false", "0, true"})
void isEven(int value, boolean expected) {
    assertEquals(expected, value % 2 == 0);
}
```
```kotlin no-run
@ParameterizedTest
@CsvSource("2, true", "3, false", "0, true")
fun isEven(value: Int, expected: Boolean) {
    assertEquals(expected, value % 2 == 0)
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 注解 | `@pytest.mark.parametrize` | `@ParameterizedTest` | `@ParameterizedTest` |
| 数据 | Python 列表，类型不限 | `@CsvSource` 等注解 | `@CsvSource` 等注解 |
| 单组失败 | 其他组继续运行 | = | = |

> 要点: 评测 Agent 时也用这个写法，每个场景是一组数据。这是「评测与安全」大类的基础。
:::

## fixture {#fixture}

fixture 准备测试需要的东西。测试函数的参数名和 fixture 名字相同就会自动注入，写法和 FastAPI 的 `Depends` 很像。

`yield` 之前是准备，之后是清理，测试失败时也会运行。`scope` 控制创建频率，默认每个测试一次。

:::compare 准备和清理
```python
import pytest

@pytest.fixture
def numbers():
    data = [1, 2]
    yield data
    data.clear()  # 清理

def test_sum(numbers: list[int]):
    assert sum(numbers) == 3

def test_append(numbers: list[int]):
    numbers.append(3)
    assert len(numbers) == 3
§ if __name__ == "__main__":
§     assert pytest.main(["-q", "-p", "no:cacheprovider", "snippet.py"]) == 0
```
```java no-run
class NumbersTest {
    List<Integer> numbers;

    @BeforeEach
    void setUp() {
        numbers = new ArrayList<>(List.of(1, 2));
    }

    @AfterEach
    void tearDown() {
        numbers.clear();
    }

    @Test
    void append() {
        numbers.add(3);
        assertEquals(3, numbers.size());
    }
}
```
```kotlin no-run
class NumbersTest {
    private val numbers = mutableListOf(1, 2)

    @AfterEach
    fun tearDown() {
        numbers.clear()
    }

    @Test
    fun append() {
        numbers.add(3)
        assertEquals(3, numbers.size)
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明 | `@pytest.fixture` | `@BeforeEach` | 属性初始化或 `@BeforeEach` |
| 注入 | 参数名匹配 | 写入成员变量 | 写入成员变量 |
| 清理 | `yield` 之后 | `@AfterEach` | `@AfterEach` |
| 共享 | `scope="session"` | `@BeforeAll` | `@BeforeAll` |
| 跨文件复用 | 放进 `conftest.py` | 继承基类或扩展 | 继承基类或扩展 |

> 要点: fixture 按需使用，测试写了参数才会运行，不像 `@BeforeEach` 那样对类里所有测试生效。
:::

pytest 自带几个常用 fixture。`tmp_path` 提供临时目录，`capsys` 捕获输出，`monkeypatch` 临时修改环境。

```python
import os
from pathlib import Path

import pytest

def test_tmp_path(tmp_path: Path):
    file = tmp_path / "note.txt"
    file.write_text("你好", encoding="utf-8")
    assert file.read_text(encoding="utf-8") == "你好"

def test_capsys(capsys: pytest.CaptureFixture):
    print("hello")
    assert capsys.readouterr().out == "hello\n"

def test_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_KEY", "test")
    assert os.environ["API_KEY"] == "test"
§ if __name__ == "__main__":
§     assert pytest.main(["-q", "-p", "no:cacheprovider", "snippet.py"]) == 0
```

## 替换依赖 {#mock}

标准库的 `unittest.mock` 相当于 Mockito 或 MockK。`Mock` 记录调用并返回指定的值，`AsyncMock` 用于协程，`patch` 临时替换模块里的名字。

:::compare 模拟依赖
```python
from unittest.mock import AsyncMock, Mock

def welcome(repo) -> str:
    return f"你好，{repo.find(1)}"

def test_welcome():
    repo = Mock()
    repo.find.return_value = "Ada"

    assert welcome(repo) == "你好，Ada"
    repo.find.assert_called_once_with(1)

async def test_async():
    client = AsyncMock()
    client.get.return_value = "ok"
    assert await client.get("/") == "ok"
§ import asyncio
§ test_welcome()
§ asyncio.run(test_async())
```
```java no-run
interface UserRepository {
    String find(int id);
}

@Test
void welcome() {
    var repo = mock(UserRepository.class);
    when(repo.find(1)).thenReturn("Ada");

    assertEquals("Ada", repo.find(1));
    verify(repo).find(1);
}
```
```kotlin no-run
interface UserRepository {
    fun find(id: Int): String
}

@Test
fun welcome() {
    val repo = mockk<UserRepository>()
    every { repo.find(1) } returns "Ada"

    assertEquals("Ada", repo.find(1))
    verify(exactly = 1) { repo.find(1) }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 创建 | `Mock()` | `mock(类)` | `mockk<类>()` |
| 设置返回值 | `.return_value = 值` | `when().thenReturn()` | `every {} returns` |
| 验证调用 | `assert_called_once_with` | `verify` | `verify` |
| 类型检查 | 默认不检查，要加 `spec` | 按类型 | 按类型 |

> 要点: `Mock()` 什么方法都接受，写错方法名也不报错。用 `Mock(spec=UserRepository)` 限制成真实类的接口。
:::

## 异步测试 {#async}

测试协程要装 `pytest-asyncio`，在函数上加 `@pytest.mark.asyncio` 就能运行。在 `pyproject.toml` 里打开自动模式后，这个标记也可以省略。

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

:::compare 测试协程
```python
import asyncio

import pytest

async def fetch() -> str:
    await asyncio.sleep(0.01)
    return "ok"

@pytest.mark.asyncio
async def test_fetch():
    assert await fetch() == "ok"
§ if __name__ == "__main__":
§     assert pytest.main(["-q", "-p", "no:cacheprovider", "snippet.py"]) == 0
```
```java no-run
@Test
void fetch() {
    var result = Mono.delay(Duration.ofMillis(10))
        .thenReturn("ok")
        .block();
    assertEquals("ok", result);
}
```
```kotlin no-run
@Test
fun fetch() = runTest {
    delay(10)
    assertEquals("ok", "ok")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 运行方式 | `pytest-asyncio` 提供事件循环 | `block()` 或 `StepVerifier` | `runTest` |
| 虚拟时间 | 不提供 | `StepVerifier.withVirtualTime` | `runTest` 自带 |

> 要点: Kotlin 的 `runTest` 会跳过 `delay`，`asyncio.sleep` 是真实等待，测试里要尽量把等待时间设短。
:::

## 测试接口和数据库 {#fastapi}

把前面的内容组合起来：用 fixture 创建内存数据库，用 `dependency_overrides` 把接口里的数据库换掉。每个测试一个全新的数据库，互不影响。

内存 SQLite 要用 `StaticPool`，否则每个连接看到的都是一个新的空数据库。

```python
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Session, SQLModel, create_engine

class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str

def get_session():
    raise RuntimeError("测试里要替换这个依赖")

app = FastAPI()

@app.post("/tasks", status_code=201)
def create_task(task: Task, session: Annotated[Session, Depends(get_session)]):
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def client(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_create_task(client: TestClient):
    response = client.post("/tasks", json={"title": "写周报"})
    assert response.status_code == 201
    assert response.json()["id"] == 1
§ if __name__ == "__main__":
§     import subprocess
§     import sys
§     assert subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "snippet.py"]).returncode == 0
```

这些 fixture 一般放进 `tests/conftest.py`，同目录下的测试文件都能用，不用导入。

:::map 测试写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `assert a == b` | `assertEquals(b, a)` | `assertEquals(b, a)` | pytest 自动显示两边的值 |
| `pytest.raises` | `assertThrows` | `assertFailsWith` | 断言异常 |
| `@pytest.mark.parametrize` | `@ParameterizedTest` | `@ParameterizedTest` | 每组数据一个测试 |
| `@pytest.fixture` | `@BeforeEach` | `@BeforeEach` | fixture 按参数名注入 |
| `conftest.py` | 测试基类 | 测试基类 | 不用导入，自动生效 |
| `Mock()` | `mock()` | `mockk()` | Python 默认不检查接口 |
| `pytest-asyncio` | `StepVerifier` | `runTest` | Python 没有虚拟时间 |
| `TestClient` | `MockMvc` | `testApplication` | 不启动真实服务 |
:::

:::recap
- 测试就是 `test_` 开头的函数，用 `assert` 判断
- 异常用 `pytest.raises`，多组数据用 `parametrize`
- fixture 通过参数名注入，`yield` 之后写清理，公共的放进 `conftest.py`
- 模拟依赖用 `unittest.mock`，加上 `spec` 防止写错方法名
- 异步测试用 `pytest-asyncio`，打开 `asyncio_mode = "auto"`
- 接口测试用 `TestClient` 和 `dependency_overrides`，内存 SQLite 要配 `StaticPool`
:::
