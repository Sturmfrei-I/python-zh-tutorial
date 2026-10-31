---
id: fastapi
part: Web 服务
title: FastAPI 入门
lede: 用类型注解声明接口，参数校验、JSON 转换和接口文档都自动完成。写过 Spring Boot 或 Retrofit 都会觉得眼熟。
source: 第一步 | https://fastapi.tiangolo.com/zh/tutorial/first-steps/ ; 请求体 | https://fastapi.tiangolo.com/zh/tutorial/body/ ; 依赖项 | https://fastapi.tiangolo.com/zh/tutorial/dependencies/ ; 并发和 async | https://fastapi.tiangolo.com/zh/async/ ; 生命周期事件 | https://fastapi.tiangolo.com/advanced/events/ ; 测试 | https://fastapi.tiangolo.com/zh/tutorial/testing/
versions: FastAPI 0.162 · Pydantic 2.14 · Spring Boot 4.1
seo_title: FastAPI 教程：路由、校验和依赖注入，对比 Spring Boot
seo_description: FastAPI 入门教程：路径和查询参数、Pydantic 请求体、错误处理、Depends 依赖注入、async 与 def 的选择、lifespan 和测试，并和 Spring Boot、Retrofit、Hilt 的写法对比。
---

## 第一个接口 {#first}

FastAPI 是用来写 HTTP 接口的 Python 框架。你用类型注解写一个函数，它负责解析请求、校验参数、把返回值转成 JSON，并生成接口文档。

先在虚拟环境里安装。`standard` 附带了开发服务器和测试要用的依赖。

```bash
pip install "fastapi[standard]"
```

:::compare 声明一个接口
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id, "name": "Ada"}

client = TestClient(app)
client.get("/users/7").json()  # => {'id': 7, 'name': 'Ada'}
```
```java no-run
§ record User(int id, String name) {}
@RestController
class UserController {
    @GetMapping("/users/{id}")
    User getUser(@PathVariable int id) {
        return new User(id, "Ada");
    }
}
```
```kotlin no-run
§ class User
interface UserApi {
    @GET("users/{id}")
    suspend fun getUser(@Path("id") id: Int): User
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 所在一端 | 服务端，收到请求后执行函数 | = | 客户端，调用方法时发出请求 |
| 实现 | 函数体就是业务逻辑 | = | 只写接口，实现由 Retrofit 生成 |
| 路由声明 | 装饰器 `@app.get` | 注解 `@GetMapping` | 注解 `@GET` |
| 路径参数 | 参数名和占位符相同就自动绑定 | 用 `@PathVariable` 绑定 | 用 `@Path` 指定 |
| 返回值 | 自动转成 JSON | 由 Jackson 转成 JSON | 由转换器解析成 `User` |

> 要点: FastAPI 和 Spring Boot 都站在服务端，装饰器相当于路由注解。Retrofit 方向相反，它描述怎么调用接口，FastAPI 描述怎么响应调用。
:::

`TestClient` 不启动服务器，直接在进程里调用接口，所以本章的示例存成一个文件就能运行。后面的示例省略了它的导入和创建。

开发时去掉 `client` 这两行，用命令启动真正的服务：

```bash
fastapi dev main.py     # 开发模式，改代码后自动重启
fastapi run main.py     # 生产模式
```

启动后打开 `http://127.0.0.1:8000/docs`，能看到自动生成的接口文档，并且可以直接在页面上发请求。

## 路径参数和查询参数 {#params}

出现在路径里的是路径参数，其他简单类型的参数是查询参数。类型注解同时负责转换和校验，`user_id: int` 收到 `abc` 时会直接返回 422，函数不会执行。

有默认值的参数是可选的。需要更细的约束时，用 `Annotated` 加上 `Query`。

:::compare 路径参数和查询参数
```python
§ from fastapi.testclient import TestClient
from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/users/{user_id}/posts")
def list_posts(
    user_id: int,
    page: Annotated[int, Query(ge=1)] = 1,
    keyword: str | None = None,
):
    return {"user": user_id, "page": page, "keyword": keyword}

§ client = TestClient(app)
data = client.get("/users/7/posts?page=2").json()
data  # => {'user': 7, 'page': 2, 'keyword': None}
client.get("/users/7/posts?page=0").status_code  # => 422
```
```java no-run
§ record PostPage() {}
§ interface Service { PostPage find(int id, int page, String keyword); }
§ Service service;
@GetMapping("/users/{id}/posts")
PostPage listPosts(
    @PathVariable int id,
    @RequestParam(defaultValue = "1") @Min(1) int page,
    @RequestParam(required = false) String keyword
) {
    return service.find(id, page, keyword);
}
```
```kotlin no-run
§ class PostPage
§ interface Api {
@GET("users/{id}/posts")
suspend fun listPosts(
    @Path("id") id: Int,
    @Query("page") page: Int = 1,
    @Query("keyword") keyword: String? = null,
): PostPage
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 路径参数 | 名字出现在路径里 | `@PathVariable` | `@Path` |
| 查询参数 | 不在路径里的简单类型 | `@RequestParam` | `@Query` |
| 可选参数 | 写默认值，没有值时用 `None` | `defaultValue` 或 `required = false` | 写默认值 |
| 取值范围 | `Query(ge=1)`，不满足时返回 422 | `@Min(1)`，不满足时返回 400 | 由服务端决定，客户端一般不校验 |

> 要点: 校验写在函数签名里，函数体拿到的参数都已经是正确的类型。
:::

## 请求体和响应模型 {#body}

JSON 请求体用 Pydantic 的 `BaseModel` 描述，字段写法和 `data class` 很像。参数类型是 `BaseModel` 子类时，FastAPI 会把它当作请求体。

`response_model` 规定响应的结构，模型里没有的字段不会发出去。创建用户的接口用它过滤掉密码。

:::compare 请求体和响应
```python
§ from fastapi import FastAPI
§ from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

§ app = FastAPI()
class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    password: str

class UserPublic(BaseModel):
    id: int
    name: str

@app.post("/users", status_code=201, response_model=UserPublic)
def create_user(user: UserCreate):
    return {"id": 1, **user.model_dump()}

§ client = TestClient(app)
body = {"name": "Ada", "password": "secret"}
response = client.post("/users", json=body)
response.status_code  # => 201
response.json()  # => {'id': 1, 'name': 'Ada'}
```
```java no-run
record UserCreate(@Size(min = 1) String name, String password) {}

record UserPublic(int id, String name) {}

@PostMapping("/users")
@ResponseStatus(HttpStatus.CREATED)
UserPublic createUser(@Valid @RequestBody UserCreate user) {
    return new UserPublic(1, user.name());
}
```
```kotlin no-run
§ interface Api {
@Serializable
data class UserCreate(
    val name: String,
    val password: String,
)

@Serializable
data class UserPublic(val id: Int, val name: String)

@POST("users")
suspend fun createUser(
    @Body user: UserCreate,
): UserPublic
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 数据模型 | 继承 `BaseModel` | `record` | `data class` |
| 请求体 | 参数类型是模型就自动识别 | `@RequestBody` | `@Body` |
| 校验时机 | 进入函数之前 | 进入方法之前，要加 `@Valid` | 反序列化时 |
| 字段约束 | `Field(min_length=1)` | `@Size(min = 1)` | 自己在 `init` 里检查 |
| 成功状态码 | 默认 200，用 `status_code` 修改 | 默认 200，用 `@ResponseStatus` 修改 | 由服务端决定 |

> 要点: 入参和出参各用一个模型，敏感字段就不会被顺手返回给客户端。
:::

`model_dump()` 把模型转成字典，相当于序列化的中间结果。

## 错误处理 {#errors}

要返回错误时，抛出 `HTTPException`。FastAPI 会停止执行，并把 `detail` 放进响应。

:::compare 返回 404
```python
§ from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException

app = FastAPI()
USERS = {1: "Ada"}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"id": user_id, "name": USERS[user_id]}

§ client = TestClient(app)
response = client.get("/users/9")
response.status_code  # => 404
response.json()  # => {'detail': '用户不存在'}
```
```java no-run
§ record User(int id, String name) {}
§ static final Map<Integer, String> USERS = Map.of(1, "Ada");
@GetMapping("/users/{id}")
User getUser(@PathVariable int id) {
    var name = USERS.get(id);
    if (name == null) {
        throw new ResponseStatusException(
            HttpStatus.NOT_FOUND, "用户不存在");
    }
    return new User(id, name);
}
```
```kotlin no-run
§ interface Api { suspend fun getUser(id: Int): String }
§ suspend fun run(api: Api) {
try {
    api.getUser(9)
} catch (e: HttpException) {
    println(e.code())
    println(e.response()?.errorBody()?.string())
}
§ }
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 所在一端 | 服务端抛出，决定返回什么 | = | 客户端捕获，决定怎么处理 |
| 错误信息 | 响应体里的 `detail` | 异常的 `reason` | 从 `errorBody` 读取 |
| 成功时 | 正常返回 | = | 不抛异常 |

> 要点: `HTTPException` 是给客户端看的。预期之外的异常会变成 500，具体内容不会发给客户端。
:::

参数校验失败时 FastAPI 自动返回 422，`detail` 是一个列表，指明哪个字段出了什么问题。

```python
§ from fastapi import FastAPI
§ from fastapi.testclient import TestClient
§ app = FastAPI()
§ @app.get("/users/{user_id}")
§ def get_user(user_id: int):
§     return {"id": user_id}
§ client = TestClient(app)
error = client.get("/users/abc").json()["detail"][0]
print(error["loc"], error["type"])
```
```output
['path', 'user_id'] int_parsing
```

## 依赖注入 {#depends}

多个接口要做同一件事时，比如检查身份、打开数据库，把它写成一个函数，再用 `Depends` 声明。FastAPI 处理请求时先运行这个函数，把返回值传给接口。

依赖函数的参数和接口一样，可以读取请求头、查询参数，也可以再依赖别的函数。

:::compare 依赖注入
```python
§ from fastapi import FastAPI, Header, HTTPException
§ from fastapi.testclient import TestClient
from typing import Annotated

from fastapi import Depends

§ app = FastAPI()
def current_user(x_token: Annotated[str, Header()]) -> str:
    if x_token != "secret":
        raise HTTPException(status_code=401, detail="令牌无效")
    return "ada"

CurrentUser = Annotated[str, Depends(current_user)]

@app.get("/me")
def read_me(user: CurrentUser):
    return {"user": user}

§ client = TestClient(app)
good = {"X-Token": "secret"}
client.get("/me", headers=good).json()  # => {'user': 'ada'}
bad = {"X-Token": "wrong"}
client.get("/me", headers=bad).status_code  # => 401
```
```java no-run
@Component
class TokenStore {
    String userOf(String token) {
        if (!"secret".equals(token)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
        }
        return "ada";
    }
}

@RestController
class MeController {
    private final TokenStore tokens;

    MeController(TokenStore tokens) {
        this.tokens = tokens;
    }

    @GetMapping("/me")
    Map<String, String> readMe(@RequestHeader("X-Token") String token) {
        return Map.of("user", tokens.userOf(token));
    }
}
```
```kotlin no-run
@Module
@InstallIn(SingletonComponent::class)
object AuthModule {
    @Provides
    fun tokenStore(): TokenStore = TokenStore()
}

class MeRepository @Inject constructor(
    private val tokens: TokenStore,
)
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明依赖 | 参数类型里写 `Depends` | 构造函数参数 | 构造函数加 `@Inject` |
| 提供依赖 | 普通函数，不用注册 | `@Component` 或 `@Bean` | `@Module` 加 `@Provides` |
| 解析时机 | 每次请求时解析 | 启动时创建好 | 编译时生成代码 |
| 默认作用域 | 一次请求内同一个依赖只运行一次 | 单例 | 不缓存，加 `@Singleton` 等注解才缓存 |
| 依赖的来源 | 可以直接读取当前请求 | 来自容器 | 来自依赖图 |

> 要点: `Depends` 比 Spring 和 Hilt 都轻，本质是「处理请求前先调用这个函数」。`Annotated` 起个别名后，多个接口写起来很短。
:::

依赖函数里用 `yield` 代替 `return`，`yield` 之后的代码会在响应发送完之后运行，用来关闭连接之类的资源。后面讲数据库时会用到这个写法。

```python
§ from fastapi import Depends, FastAPI
§ from fastapi.testclient import TestClient
§ from typing import Annotated
§ app = FastAPI()
def get_connection():
    print("打开连接")
    try:
        yield "connection"
    finally:
        print("关闭连接")

@app.get("/ping")
def ping(connection: Annotated[str, Depends(get_connection)]):
    print("处理请求")
    return {"ok": True}

§ TestClient(app).get("/ping")
```
```output
打开连接
处理请求
关闭连接
```

## async def 还是 def {#async}

FastAPI 同时支持两种写法，它们的运行位置不同：

- `async def` 直接运行在事件循环上。事件循环是单线程的，所以函数里只能 `await`，不能阻塞。
- `def` 被放到线程池里运行，阻塞也不会影响其他请求。

事件循环可以类比成 Android 的主线程。在主线程上做耗时操作会卡住界面，在 `async def` 里调用阻塞函数会卡住所有请求。Spring MVC 每个请求占一个线程，更接近这里的 `def`，WebFlux 才接近 `async def`。

:::compare 不要阻塞事件循环
```python
§ from fastapi.testclient import TestClient
import asyncio
import time

from fastapi import FastAPI

app = FastAPI()

@app.get("/good")
async def good():
    await asyncio.sleep(0.01)  # 挂起，事件循环去处理别的请求
    return {"ok": True}

@app.get("/bad")
async def bad():
    time.sleep(0.01)  # 阻塞，所有请求都要等它
    return {"ok": True}

@app.get("/fine")
def fine():
    time.sleep(0.01)  # 在线程池里运行，不影响别的请求
    return {"ok": True}

§ client = TestClient(app)
§ assert [client.get(p).status_code for p in ("/good", "/bad", "/fine")] == [200, 200, 200]
```
```java no-run
// WebFlux 运行在事件循环上
@GetMapping("/good")
Mono<String> good() {
    return Mono.delay(Duration.ofMillis(10))  // 不占线程
        .thenReturn("ok");
}

@GetMapping("/bad")
Mono<String> bad() throws InterruptedException {
    Thread.sleep(10);  // 阻塞，所有请求都要等它
    return Mono.just("ok");
}

@GetMapping("/fine")
Mono<String> fine() {
    return Mono.fromCallable(() -> {
        Thread.sleep(10);  // 放到线程池，不影响别的请求
        return "ok";
    }).subscribeOn(Schedulers.boundedElastic());
}
```
```kotlin no-run
// 运行在 Dispatchers.Main 上
suspend fun good() {
    delay(10)  // 挂起，主线程继续处理别的事
}

suspend fun bad() {
    Thread.sleep(10)  // 阻塞，界面跟着卡住
}

suspend fun fine() = withContext(Dispatchers.IO) {
    Thread.sleep(10)  // 切到后台线程，不影响主线程
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 可挂起的函数 | `async def` | 返回 `Mono` 的方法 | `suspend fun` |
| 挂起点 | `await` | 操作符链 | 调用其他挂起函数 |
| 单线程调度器 | 事件循环 | Netty 事件循环 | `Dispatchers.Main` |
| 阻塞代码放哪 | 写成 `def`，由框架放进线程池 | `subscribeOn(boundedElastic())` | `withContext(Dispatchers.IO)` |

> 要点: 所有调用都支持 `await` 时写 `async def`，用到阻塞的库时写 `def`，拿不准也写 `def`。最危险的写法是在 `async def` 里调用阻塞函数。
:::

调用外部 HTTP 接口时，`requests` 是阻塞的，在 `async def` 里要换成 `httpx.AsyncClient`。事件循环的基础知识见 Python 语言部分的「异步编程和异步生成器」。

## 拆分路由 {#router}

接口多了以后，用 `APIRouter` 按业务拆到不同文件，作用类似把 Retrofit 接口拆成多个 `interface`。

```python
§ from fastapi import FastAPI
§ from fastapi.testclient import TestClient
from fastapi import APIRouter

users = APIRouter(prefix="/users", tags=["users"])

@users.get("/{user_id}")
def get_user(user_id: int):
    return {"id": user_id}

§ app = FastAPI()
app.include_router(users, prefix="/api")

§ client = TestClient(app)
client.get("/api/users/7").json()  # => {'id': 7}
```

## 启动和关闭 {#lifespan}

有些资源只该创建一次，比如 HTTP 客户端或数据库连接池。把它们写进 `lifespan`，`yield` 之前的代码在服务启动时运行，之后的代码在关闭时运行，作用类似 `Application.onCreate`。

```python
§ from fastapi import FastAPI, Request
§ from fastapi.testclient import TestClient
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.greeting = "你好"  # 启动时运行
    yield
    print("服务关闭")  # 关闭时运行

app = FastAPI(lifespan=lifespan)

@app.get("/hello")
def hello(request: Request):
    return {"message": request.app.state.greeting}

with TestClient(app) as client:
    print(client.get("/hello").json())
```
```output
{'message': '你好'}
服务关闭
```

`TestClient` 要写在 `with` 里，`lifespan` 才会运行。

:::warn 不要用 on_event
旧资料里的 `@app.on_event("startup")` 已经弃用。`lifespan` 和它不能混用，新代码统一用 `lifespan`。
:::

## 测试 {#testing}

`TestClient` 配合 pytest 就是接口测试。pytest 要单独安装，测试函数以 `test_` 开头，用普通的 `assert` 判断。

要替换依赖时，用 `dependency_overrides` 指定一个假的函数，接口代码不用改动。

:::compare 替换依赖来测试
```python
§ from typing import Annotated
§ from fastapi import Depends, FastAPI
§ from fastapi.testclient import TestClient
§ app = FastAPI()
def current_user() -> str:
    raise RuntimeError("测试里不该调用真实的认证")

@app.get("/me")
def read_me(user: Annotated[str, Depends(current_user)]):
    return {"user": user}

def test_read_me():
    app.dependency_overrides[current_user] = lambda: "tester"
    client = TestClient(app)
    assert client.get("/me").json() == {"user": "tester"}
    app.dependency_overrides.clear()
§ test_read_me()
```
```java no-run
§ class TokenStore { String userOf(String token) { return token; } }
§ class MeController {}
@WebMvcTest(MeController.class)
class MeControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean TokenStore tokens;

    @Test
    void readsUser() throws Exception {
        when(tokens.userOf("t")).thenReturn("tester");
        mvc.perform(get("/me").header("X-Token", "t"))
            .andExpect(jsonPath("$.user").value("tester"));
    }
}
```
```kotlin no-run
@HiltAndroidTest
class MeRepositoryTest {
    @get:Rule
    val hiltRule = HiltAndroidRule(this)

    @BindValue
    val tokens: TokenStore = FakeTokenStore()

    @Inject
    lateinit var repository: MeRepository

    @Test
    fun readsUser() {
        hiltRule.inject()
        assertEquals("tester", repository.currentUser())
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 测试框架 | pytest | JUnit | JUnit |
| 断言 | `assert` 语句 | `assertEquals` 等函数 | `assertEquals` 等函数 |
| 发现测试 | 函数名以 `test_` 开头 | `@Test` 注解 | `@Test` 注解 |
| 替换依赖 | `app.dependency_overrides` | `@MockitoBean` | `@BindValue`、`@TestInstallIn` |

> 要点: 记得在测试结束时清空 `dependency_overrides`，否则替换会影响后面的测试。
:::

:::map FastAPI、Spring Boot 和 Android 写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `@app.get("/users/{id}")` | `@GetMapping` | `@GET("users/{id}")` | Retrofit 在客户端，另外两个在服务端 |
| `Query(ge=1)` | `@Min(1)` | `@Query` | Retrofit 不校验 |
| `BaseModel` | `record` | `data class` | Pydantic 在运行时校验 |
| `HTTPException` | `ResponseStatusException` | `HttpException` | Retrofit 的异常由客户端捕获 |
| `Depends` | 构造函数注入 | Hilt | `Depends` 每次请求时解析 |
| `async def` | WebFlux 的 `Mono` | `suspend fun` | 都不能在里面阻塞线程 |
| `lifespan` | `@PostConstruct`、`@PreDestroy` | `Application.onCreate` | `lifespan` 把启动和关闭写在一起 |
| `TestClient` | `MockMvc` | `MockWebServer` | `MockWebServer` 模拟的是服务端 |
:::

:::recap
- FastAPI 用函数签名声明接口：路径参数、查询参数和请求体都靠类型注解区分
- 入参和出参分别用 Pydantic 模型，`response_model` 负责过滤字段
- `HTTPException` 返回预期的错误，校验失败自动返回 422
- `Depends` 在处理请求前运行函数，`yield` 之后的代码负责清理
- `async def` 里不能阻塞，用到阻塞的库时写 `def`
- 只创建一次的资源放进 `lifespan`，测试时用 `TestClient` 和 `dependency_overrides`
:::
