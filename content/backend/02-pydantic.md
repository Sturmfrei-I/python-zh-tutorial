---
id: pydantic
part: Web 服务
title: Pydantic 数据校验
lede: 外部进来的数据都不可信，大模型返回的 JSON 更是如此。Pydantic 用类型注解声明结构，在运行时校验并转换数据。
source: 模型 | https://docs.pydantic.dev/latest/concepts/models/ ; 字段 | https://docs.pydantic.dev/latest/concepts/fields/ ; 校验器 | https://docs.pydantic.dev/latest/concepts/validators/ ; 序列化 | https://docs.pydantic.dev/latest/concepts/serialization/ ; JSON Schema | https://docs.pydantic.dev/latest/concepts/json_schema/ ; 配置管理 | https://docs.pydantic.dev/latest/concepts/pydantic_settings/
versions: Pydantic 2.14 · pydantic-settings 2.16 · Jackson 2
seo_title: Pydantic 教程：字段校验、序列化和 JSON Schema
seo_description: Pydantic v2 入门：BaseModel、类型转换、Field 约束、校验器、序列化、联合类型、JSON Schema 和配置管理，并和 Java record、Jackson、Kotlin data class 对比。
---

## 为什么要校验 {#why}

Python 的类型注解默认只给工具和人看，运行时不检查。`user.age = "很大"` 不会报错。

Java 和 Kotlin 在反序列化时会按类型检查，Python 要靠 Pydantic 补上这一步。它有三个用途：

- 校验外部输入，比如请求体、配置和数据库之外的数据
- 把 JSON 转成带类型的对象，或者反过来
- 生成 JSON Schema，大模型的结构化输出和工具调用都要用到

FastAPI 和 SQLModel 都建立在 Pydantic 之上，所以这一章学的内容在后面处处都会用到。

```bash
pip install pydantic
```

## 定义模型 {#model}

继承 `BaseModel`，用类型注解写字段。创建对象时 Pydantic 会校验数据，失败时抛 `ValidationError`。

:::compare 定义数据模型
```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    tags: list[str] = []
    bio: str | None = None

user = User(id=1, name="Ada")
user  # => User(id=1, name='Ada', tags=[], bio=None)
user.name  # => 'Ada'
```
```java no-run
record User(int id, String name, List<String> tags, String bio) {
    User {
        tags = tags == null ? List.of() : tags;
    }
}
```
```kotlin no-run
@Serializable
data class User(
    val id: Int,
    val name: String,
    val tags: List<String> = emptyList(),
    val bio: String? = null,
)
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明 | 继承 `BaseModel` | `record` | `data class` |
| 校验时机 | 创建对象时 | 反序列化时只查类型 | 反序列化时查类型 |
| 可选字段 | `str \| None = None` | 可为 `null` 的引用类型 | `String? = null` |
| 默认值 | 直接写在字段后 | 写在紧凑构造函数里 | 写在参数后 |
| 可变性 | 默认可变 | 不可变 | `val` 不可变 |

> 要点: 默认值 `[]` 在 `BaseModel` 里是安全的，Pydantic 会为每个对象复制一份。普通函数的默认参数不能这样写。
:::

## 类型转换 {#coerce}

Pydantic 默认不是严格模式，会尽量把数据转成目标类型。字符串 `"1"` 能变成整数 `1`，Jackson 和 kotlinx.serialization 默认也接受这种写法。

校验失败时，异常里列出了每个字段的问题，不是遇到第一个就停止。

:::compare 转换和校验失败
```python
from pydantic import BaseModel, ValidationError

class User(BaseModel):
    id: int
    name: str

User(id="1", name="Ada").id  # => 1

try:
    User(id="abc")
except ValidationError as e:
    print([(x["loc"], x["type"]) for x in e.errors()])  # => [(('id',), 'int_parsing'), (('name',), 'missing')]
```
```java no-run
§ record User(int id, String name) {}
void run() throws Exception {
    var mapper = new ObjectMapper();
    var user = mapper.readValue(
        "{\"id\": \"1\", \"name\": \"Ada\"}", User.class);
    System.out.println(user.id());  // 1

    // 遇到第一个错误就抛异常
    mapper.readValue("{\"id\": \"abc\"}", User.class);
}
```
```kotlin no-run
@Serializable
data class User(val id: Int, val name: String)

fun main() {
    val user = Json.decodeFromString<User>(
        """{"id": "1", "name": "Ada"}""",
    )
    println(user.id)  // 1

    // 遇到第一个错误就抛异常
    Json.decodeFromString<User>("""{"id": "abc"}""")
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| `"1"` 转 `int` | 默认转换 | 默认转换 | 默认转换 |
| 多个错误 | 一次全部列出 | 只报第一个 | 只报第一个 |
| 关闭转换 | `strict=True` | 关闭 `ALLOW_COERCION_OF_SCALARS` | 自定义序列化器 |

> 要点: `e.errors()` 里的 `loc` 是字段路径，`type` 是错误类型。把它们交给大模型，它就知道该改哪里，这是自动重试的基础。
:::

需要更严格时，用 `model_config` 配置模型。常用的有三个选项：

```python
from pydantic import BaseModel, ConfigDict, ValidationError

class Event(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    id: int

def reason(**data) -> str:
    try:
        Event(**data)
    except ValidationError as e:
        return e.errors()[0]["type"]
    return "通过"

reason(id=1)  # => '通过'
reason(id="1")  # => 'int_type'
reason(id=1, name="x")  # => 'extra_forbidden'
```

- `strict=True`：不做类型转换
- `frozen=True`：对象不可修改，相当于 `record`
- `extra="forbid"`：出现未声明的字段时报错。默认是忽略

## 字段约束 {#field}

`Field` 声明取值范围、长度和默认值。字段有默认值时可变对象用 `default_factory`。

:::compare 字段约束
```python
from pydantic import BaseModel, Field, ValidationError

class Order(BaseModel):
    title: str = Field(min_length=1, max_length=20)
    amount: int = Field(gt=0, description="金额，单位是分")
    items: list[str] = Field(default_factory=list)

Order(title="咖啡", amount=3000).amount  # => 3000

try:
    Order(title="", amount=0)
except ValidationError as e:
    print(e.error_count())  # => 2
```
```java no-run
record Order(
    @Size(min = 1, max = 20) String title,
    @Positive int amount,
    List<String> items
) {}

void check(Validator validator, Order order) {
    var errors = validator.validate(order);
    System.out.println(errors.size());
}
```
```kotlin no-run
data class Order(
    val title: String,
    val amount: Int,
    val items: List<String> = emptyList(),
) {
    init {
        require(title.length in 1..20) { "标题长度不对" }
        require(amount > 0) { "金额要大于 0" }
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明位置 | `Field` | Bean Validation 注解 | `init` 里写 `require` |
| 何时检查 | 创建对象时 | 调用 `validate` 时 | 创建对象时 |
| 能否创建非法对象 | 不能 | 能 | 不能 |
| 字段说明 | `description` 进入 JSON Schema | 另加文档注解 | 另加文档注解 |

> 要点: `description` 不只是注释。生成工具定义时它会发给大模型，写清楚了模型才知道怎么填。
:::

## 自定义校验 {#validators}

`Field` 表达不了的规则写成校验器。`field_validator` 检查单个字段，`model_validator` 检查多个字段之间的关系。

```python
from pydantic import BaseModel, ValidationError, field_validator, model_validator

class Booking(BaseModel):
    email: str
    start: int
    end: int

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("邮箱格式不对")
        return value.lower()

    @model_validator(mode="after")
    def check_range(self):
        if self.end <= self.start:
            raise ValueError("结束时间要晚于开始时间")
        return self

Booking(email="A@B.com", start=1, end=2).email  # => 'a@b.com'

try:
    Booking(email="a@b.com", start=2, end=1)
except ValidationError as e:
    print(e.errors()[0]["msg"])  # => Value error, 结束时间要晚于开始时间
```

校验器可以返回新的值，所以也用来做规范化，比如去空格、转小写。校验失败时抛 `ValueError`，不要抛 `ValidationError`。

## 序列化 {#serialize}

`model_dump()` 转成字典，`model_dump_json()` 转成 JSON 字符串。反方向用 `model_validate()` 和 `model_validate_json()`。

:::compare JSON 和对象互转
```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    password: str = ""

user = User.model_validate_json('{"id": 1, "name": "Ada"}')
user.name  # => 'Ada'

user.model_dump(exclude={"password"})  # => {'id': 1, 'name': 'Ada'}
user.model_dump_json(exclude={"password"})  # => '{"id":1,"name":"Ada"}'
```
```java no-run
§ record User(int id, String name) {}
void run() throws Exception {
    var mapper = new ObjectMapper();
    var user = mapper.readValue(
        "{\"id\": 1, \"name\": \"Ada\"}", User.class);
    var json = mapper.writeValueAsString(user);
    System.out.println(json);
}
```
```kotlin no-run
@Serializable
data class User(val id: Int, val name: String)

fun main() {
    val user = Json.decodeFromString<User>(
        """{"id": 1, "name": "Ada"}""",
    )
    println(Json.encodeToString(user))
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| JSON 转对象 | `Model.model_validate_json(s)` | `mapper.readValue` | `Json.decodeFromString` |
| 对象转 JSON | `obj.model_dump_json()` | `mapper.writeValueAsString` | `Json.encodeToString` |
| 字段改名 | `Field(alias="userName")` | `@JsonProperty` | `@SerialName` |
| 排除字段 | `exclude` 参数 | `@JsonIgnore` | `@Transient` |
| 复制并修改 | `model_copy(update={...})` | 自己写 `with` 方法 | `copy()` |

> 要点: 校验 JSON 字符串时直接用 `model_validate_json`。它比先 `json.loads` 再校验更快，错误信息也更准确。
:::

`model_dump()` 不写参数时保留 Python 对象，比如 `datetime`。要转成能写入 JSON 的值，用 `model_dump(mode="json")`。

## 嵌套和联合类型 {#nested}

字段的类型可以是另一个模型，校验会逐层进行。一个字段可能有多种结构时，用带标记的联合类型，标记字段决定用哪个模型，相当于 `sealed class`。

:::compare 带标记的联合类型
```python
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

class TextBlock(BaseModel):
    type: Literal["text"]
    text: str

class ImageBlock(BaseModel):
    type: Literal["image"]
    url: str

Block = Annotated[TextBlock | ImageBlock, Field(discriminator="type")]

adapter = TypeAdapter(list[Block])
blocks = adapter.validate_python([
    {"type": "text", "text": "你好"},
    {"type": "image", "url": "a.png"},
])
[type(block).__name__ for block in blocks]  # => ['TextBlock', 'ImageBlock']
```
```java no-run
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "type")
@JsonSubTypes({
    @JsonSubTypes.Type(value = TextBlock.class, name = "text"),
    @JsonSubTypes.Type(value = ImageBlock.class, name = "image"),
})
sealed interface Block permits TextBlock, ImageBlock {}

record TextBlock(String text) implements Block {}

record ImageBlock(String url) implements Block {}
```
```kotlin no-run
@Serializable
@JsonClassDiscriminator("type")
sealed interface Block

@Serializable
@SerialName("text")
data class TextBlock(val text: String) : Block

@Serializable
@SerialName("image")
data class ImageBlock(val url: String) : Block
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 表示多种结构 | `A \| B` | `sealed interface` | `sealed interface` |
| 标记字段 | `discriminator="type"` | `@JsonTypeInfo` | `@JsonClassDiscriminator` |
| 处理各分支 | `match` 或 `isinstance` | `switch` 模式匹配 | `when` |

> 要点: `TypeAdapter` 用来校验不是 `BaseModel` 的类型，比如 `list[Block]`。大模型接口的消息内容就是这种结构。
:::

## 生成 JSON Schema {#schema}

`model_json_schema()` 把模型转成 JSON Schema，字段类型、约束和说明都在里面。这是后面工具调用和结构化输出的关键一步。

```python
from pydantic import BaseModel, Field

class Weather(BaseModel):
    """查询某个城市的天气"""
    city: str = Field(description="城市名")
    days: int = Field(default=1, ge=1, le=7)

schema = Weather.model_json_schema()
schema["description"]  # => '查询某个城市的天气'
schema["required"]  # => ['city']
schema["properties"]["days"]  # => {'default': 1, 'maximum': 7, 'minimum': 1, 'title': 'Days', 'type': 'integer'}
```

类的文档字符串会成为 `description`，字段的 `description` 也会保留。

## 读取配置 {#settings}

`pydantic-settings` 从环境变量和 `.env` 文件读取配置并校验，缺少配置时启动就报错，不用等到调用时才发现。

:::compare 读取配置
```python
§ import os
§ os.environ["API_KEY"] = "sk-test"
§ os.environ["DEBUG"] = "true"
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    api_key: str
    database_url: str = "sqlite:///app.db"
    debug: bool = False

settings = Settings()
settings.debug  # => True
settings.database_url  # => 'sqlite:///app.db'
```
```java no-run
@ConfigurationProperties(prefix = "app")
record Settings(
    String apiKey,
    @DefaultValue("jdbc:sqlite:app.db") String databaseUrl,
    @DefaultValue("false") boolean debug
) {}
```
```kotlin no-run
data class Settings(
    val apiKey: String = System.getenv("API_KEY")
        ?: error("缺少 API_KEY"),
    val databaseUrl: String = System.getenv("DATABASE_URL")
        ?: "jdbc:sqlite:app.db",
)
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 来源 | 环境变量、`.env` | `application.properties`、环境变量 | 自己读取 |
| 名称匹配 | 不区分大小写 | 宽松匹配 | 自己写 |
| 类型转换 | 自动 | 自动 | 自己写 |
| 缺少配置 | 启动时报错 | 绑定时为 `null`，要加校验 | 自己处理 |

> 要点: API Key 这类密钥放在环境变量或 `.env` 里，把 `.env` 加进 `.gitignore`。
:::

:::map Pydantic 写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `BaseModel` | `record` | `data class` | Pydantic 在运行时校验 |
| `Field(gt=0)` | `@Positive` | `require()` | 非法对象创建不出来 |
| `field_validator` | 自定义校验注解 | `init` | 校验器还能改写值 |
| `model_validate_json()` | `mapper.readValue()` | `Json.decodeFromString()` | 反序列化 |
| `model_dump_json()` | `mapper.writeValueAsString()` | `Json.encodeToString()` | 序列化 |
| `model_copy(update=...)` | 自己实现 | `copy()` | 不修改原对象 |
| `Field(discriminator=...)` | `@JsonTypeInfo` | `@JsonClassDiscriminator` | 按标记字段选模型 |
| `BaseSettings` | `@ConfigurationProperties` | 自己读取 | 启动时校验配置 |
:::

:::recap
- Python 的类型注解默认不检查，外部数据要交给 Pydantic 校验
- `BaseModel` 创建时校验，默认会转换类型，严格模式用 `strict=True`
- 字段约束用 `Field`，复杂规则用 `field_validator` 和 `model_validator`
- `model_dump`、`model_dump_json` 负责输出，`model_validate`、`model_validate_json` 负责输入
- 多种结构用带标记的联合类型，非模型类型用 `TypeAdapter`
- `model_json_schema()` 生成 JSON Schema，`description` 会发给大模型
- 配置和密钥用 `BaseSettings` 读取，缺少时启动就报错
:::
