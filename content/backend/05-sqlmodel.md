---
id: sqlite-sqlmodel
part: 数据存储
title: SQLite 与 SQLModel
lede: 服务端用的 SQLite 和 Android 上 Room 底层的是同一个数据库。SQLModel 用一个类同时描述表和数据，既像 Room，也像 JPA。
source: FastAPI 使用 SQL 数据库 | https://fastapi.tiangolo.com/zh/tutorial/sql-databases/ ; SQLModel 教程 | https://sqlmodel.tiangolo.com/tutorial/ ; sqlite3 模块 | https://docs.python.org/zh-cn/3.12/library/sqlite3.html ; Alembic 教程 | https://alembic.sqlalchemy.org/en/latest/tutorial.html ; WAL 模式 | https://www.sqlite.org/wal.html ; Room 数据库 | https://developer.android.com/training/data-storage/room
versions: SQLModel 0.0.48 · SQLAlchemy 2.1 · Alembic 1.20 · Spring Data JPA · Flyway 13
seo_title: SQLModel 教程：SQLite 接入 FastAPI，对比 JPA 和 Room
seo_description: SQLite 和 SQLModel 入门：定义表、增删改查、接入 FastAPI、外键关系、Alembic 迁移和并发写入，并和 JPA、Flyway、Android Room 的写法对比。
---

## 从 SQLite 开始 {#sqlite}

SQLite 不需要单独的数据库服务，一个文件就是一个数据库。它是 Android 自带的数据库，Python 标准库也带了 `sqlite3` 模块，小型服务和开发环境用它就够了。

:::compare 直接写 SQL
```python
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE task (id INTEGER PRIMARY KEY, title TEXT)")
db.execute("INSERT INTO task (title) VALUES (?)", ("写周报",))
db.commit()

row = db.execute("SELECT title FROM task WHERE id = ?", (1,))
row.fetchone()  # => ('写周报',)
```
```java no-run
§ void run() throws Exception {
try (var db = DriverManager.getConnection("jdbc:sqlite::memory:")) {
    db.createStatement().execute(
        "CREATE TABLE task (id INTEGER PRIMARY KEY, title TEXT)");

    var insert = db.prepareStatement(
        "INSERT INTO task (title) VALUES (?)");
    insert.setString(1, "写周报");
    insert.executeUpdate();

    var query = db.prepareStatement(
        "SELECT title FROM task WHERE id = ?");
    query.setInt(1, 1);
    var rows = query.executeQuery();
    rows.next();
    System.out.println(rows.getString(1));
}
§ }
```
```kotlin no-run
val db = helper.writableDatabase
db.execSQL("CREATE TABLE task (id INTEGER PRIMARY KEY, title TEXT)")
db.execSQL("INSERT INTO task (title) VALUES (?)", arrayOf("写周报"))

db.rawQuery(
    "SELECT title FROM task WHERE id = ?",
    arrayOf("1"),
).use { cursor ->
    cursor.moveToFirst()
    println(cursor.getString(0))
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 打开数据库 | `sqlite3.connect(路径)` | `DriverManager.getConnection` | `SQLiteOpenHelper` |
| 参数占位符 | `?` | = | = |
| 提交 | 写入后要调用 `commit()` | 默认自动提交 | 不开事务时自动提交 |
| 读取结果 | 元组 | `ResultSet` | `Cursor` |

> 要点: 参数一定要用占位符传，不要拼进 SQL 字符串，否则会有 SQL 注入风险。
:::

直接写 SQL 要手动转换类型，字段一多就很繁琐。SQLModel 基于 SQLAlchemy 和 Pydantic，把表和数据模型合成一个类，定位接近 Room，也接近 Java 的 JPA。

```bash
pip install sqlmodel
```

## 定义表 {#models}

:::compare 定义表
```python
from sqlmodel import Field, SQLModel

class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    done: bool = False
```
```java no-run
@Entity
@Table(indexes = @Index(columnList = "title"))
class Task {
    @Id @GeneratedValue Long id;
    String title;
    boolean done = false;
}
```
```kotlin no-run
@Entity(tableName = "task")
data class Task(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    @ColumnInfo(index = true) val title: String,
    val done: Boolean = false,
)
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明成表 | `table=True` | `@Entity` | `@Entity` |
| 默认表名 | 类名转小写 | 类名，Spring Boot 转成小写 | 类名 |
| 主键 | `primary_key=True` | `@Id` | `@PrimaryKey` |
| 自增主键的初始值 | `None`，写入后才有值 | `null`，写入后才有值 | `0` |
| 索引 | `Field(index=True)` | `@Table(indexes = ...)` | `@ColumnInfo(index = true)` |

> 要点: `id` 写成 `int | None` 是因为对象创建时还没有主键，这个值由数据库生成。
:::

## 连接数据库 {#engine}

`engine` 管理数据库连接，整个应用只创建一个，放在模块顶层就行。`create_all` 创建还不存在的表。

:::compare 打开数据库
```python
§ from sqlmodel import Field, SQLModel
§ class Task(SQLModel, table=True):
§     id: int | None = Field(default=None, primary_key=True)
from sqlmodel import create_engine

engine = create_engine("sqlite:///app.db")
SQLModel.metadata.create_all(engine)
```
```java no-run
@SpringBootApplication
public class App {
    public static void main(String[] args) {
        SpringApplication.run(App.class, args);
    }
}

// application.properties
// spring.datasource.url=jdbc:sqlite:app.db
// spring.jpa.hibernate.ddl-auto=update
```
```kotlin no-run
@Database(entities = [Task::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun taskDao(): TaskDao
}

val db = Room.databaseBuilder(
    context,
    AppDatabase::class.java,
    "app.db",
).build()
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 入口对象 | `engine` | 自动配置的 `DataSource` | `AppDatabase` |
| 创建次数 | 只创建一次 | = | = |
| 创建表 | 调用 `create_all` | 由 `ddl-auto` 配置 | 首次打开时自动创建 |
| 查看 SQL | `create_engine(..., echo=True)` | `spring.jpa.show-sql=true` | `setQueryCallback` |

> 要点: `sqlite:///app.db` 里的三个斜杠表示相对路径，文件在当前目录下。
:::

## 增删改查 {#crud}

Room 把操作写在 `@Dao` 接口里，SQLModel 则通过 `Session` 完成。`Session` 会跟踪取出来的对象，修改属性之后 `commit`，改动就写回数据库，这一点和 JPA 的 `EntityManager` 相同。

:::compare 增删改查
```python
§ from sqlmodel import Field, SQLModel, create_engine
§ class Task(SQLModel, table=True):
§     id: int | None = Field(default=None, primary_key=True)
§     title: str = Field(index=True)
§     done: bool = False
§ engine = create_engine("sqlite://")
§ SQLModel.metadata.create_all(engine)
from sqlmodel import Session, select

with Session(engine) as session:
    task = Task(title="写周报")
    session.add(task)
    session.commit()
    session.refresh(task)  # 读回数据库生成的 id
    print(task.id)  # => 1

with Session(engine) as session:
    query = select(Task).where(Task.title == "写周报")
    found = session.exec(query).one()
    found.done = True
    session.commit()

with Session(engine) as session:
    task = session.get(Task, 1)
    print(task.done)  # => True
    session.delete(task)
    session.commit()
```
```java no-run
§ @Entity class Task { @Id Long id; String title; boolean done; }
interface TaskRepository extends JpaRepository<Task, Long> {
    Optional<Task> findByTitle(String title);
}

@Service
class TaskService {
    private final TaskRepository tasks;

    TaskService(TaskRepository tasks) {
        this.tasks = tasks;
    }

    Task create(String title) {
        var task = new Task();
        task.title = title;
        return tasks.save(task);
    }

    @Transactional
    void finish(String title) {
        var task = tasks.findByTitle(title).orElseThrow();
        task.done = true;  // 事务提交时自动写回
    }

    void remove(long id) {
        tasks.deleteById(id);
    }
}
```
```kotlin no-run
§ @Entity data class Task(@PrimaryKey val id: Int = 0)
@Dao
interface TaskDao {
    @Insert
    suspend fun insert(task: Task): Long

    @Query("SELECT * FROM task WHERE title = :title")
    suspend fun find(title: String): Task?

    @Query("SELECT * FROM task WHERE id = :id")
    suspend fun get(id: Int): Task?

    @Update
    suspend fun update(task: Task)

    @Delete
    suspend fun delete(task: Task)
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 操作入口 | `Session` | `JpaRepository` | `@Dao` 接口 |
| 写查询 | 用 `select` 在代码里拼 | 方法名或 JPQL | 在注解里写 SQL |
| 查询检查 | 运行时才发现错误 | 启动时检查方法名 | 编译时检查 SQL |
| 修改数据 | 改对象属性再 `commit` | 在事务里改对象属性 | 调用 `@Update` |
| 事务 | `commit` 提交，异常时回滚 | `@Transactional` | 单个方法自动事务，多个用 `withTransaction` |
| 线程 | 同步调用，会阻塞 | = | `suspend` 方法自动在后台线程运行 |

> 要点: 没有 `commit` 的改动不会保存。`with` 块结束时 `Session` 关闭，未提交的内容被丢弃。
:::

查询结果常用这几个方法：`.all()` 取全部，`.first()` 取第一条，没有时返回 `None`，`.one()` 要求恰好一条，否则抛异常。`select` 后面还可以接 `.order_by()`、`.offset()` 和 `.limit()`。

## 接入 FastAPI {#fastapi}

把前面的内容组合起来。每个请求用 `Depends` 拿到一个独立的 `Session`，请求结束后自动关闭。

```python
§ from fastapi.testclient import TestClient
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine

engine = create_engine(
    "sqlite:///app.db",
    connect_args={"check_same_thread": False},
)

class TaskBase(SQLModel):
    title: str

class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    done: bool = False

class TaskCreate(TaskBase):
    pass

class TaskPublic(TaskBase):
    id: int
    done: bool

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/tasks", status_code=201, response_model=TaskPublic)
def create_task(data: TaskCreate, session: SessionDep):
    task = Task.model_validate(data)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@app.get("/tasks/{task_id}", response_model=TaskPublic)
def get_task(task_id: int, session: SessionDep):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

with TestClient(app) as client:
    created = client.post("/tasks", json={"title": "写周报"}).json()
    print(created)  # => {'title': '写周报', 'id': 1, 'done': False}
    print(client.get("/tasks/9").status_code)  # => 404
```

这段代码有四个地方要注意：

- **模型要分开。** `Task` 对应数据库表，`TaskCreate` 规定客户端能传什么，`TaskPublic` 规定返回什么。这样客户端没法自己设置 `id` 和 `done`，以后加了敏感字段也不会漏出去。
- **`check_same_thread=False`。** Python 的 `sqlite3` 默认不允许跨线程使用同一个连接，而一次请求可能经过线程池里的不同线程。每个请求都有自己的 `Session`，所以这样设置是安全的。
- **接口用 `def`。** `Session` 是阻塞的，要放在线程池里运行。写成 `async def` 会卡住事件循环。
- **响应模型用 `response_model`。** 函数返回的是 `Task`，由 FastAPI 转换成 `TaskPublic`。

## 表之间的关系 {#relations}

外键用 `foreign_key` 声明，`Relationship` 让你能直接通过属性访问关联对象。

:::compare 一对多关系
```python
§ from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    members: list["Member"] = Relationship(back_populates="team")

class Member(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    team_id: int | None = Field(default=None, foreign_key="team.id")
    team: Team | None = Relationship(back_populates="members")

§ engine = create_engine("sqlite://")
§ SQLModel.metadata.create_all(engine)
with Session(engine) as session:
    session.add(Team(name="客户端", members=[Member(name="Ada")]))
    session.commit()
    member = session.exec(select(Member)).one()
    print(member.team.name)  # => 客户端
```
```java no-run
@Entity
class Team {
    @Id @GeneratedValue Long id;
    String name;

    @OneToMany(mappedBy = "team", cascade = CascadeType.ALL)
    List<Member> members = new ArrayList<>();
}

@Entity
class Member {
    @Id @GeneratedValue Long id;
    String name;

    @ManyToOne
    Team team;
}
```
```kotlin no-run
@Entity
data class Team(
    @PrimaryKey val id: Int,
    val name: String,
)

@Entity(
    foreignKeys = [ForeignKey(
        entity = Team::class,
        parentColumns = ["id"],
        childColumns = ["teamId"],
    )],
)
data class Member(
    @PrimaryKey val id: Int,
    val name: String,
    @ColumnInfo(index = true) val teamId: Int?,
)

data class TeamWithMembers(
    @Embedded val team: Team,
    @Relation(parentColumn = "id", entityColumn = "teamId")
    val members: List<Member>,
)
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 外键 | `Field(foreign_key="team.id")` | `@ManyToOne` | `@ForeignKey` |
| 读取关联数据 | 访问属性时才查询 | `@OneToMany` 默认也是访问时才查询 | 查询时用 `@Relation` 一次取出 |
| 外键约束 | SQLite 默认不检查，要自己打开 | 用 SQLite 时同样要打开 | Room 自动打开 |

> 要点: 访问关联属性时才会发查询，在循环里访问可能产生大量 SQL，这时候要在 `select` 里提前关联。
:::

SQLite 默认不检查外键，要在每个连接上打开：

```python
§ from sqlalchemy.exc import IntegrityError
§ from sqlmodel import Field, Session, SQLModel, create_engine
§ class Team(SQLModel, table=True):
§     id: int | None = Field(default=None, primary_key=True)
§ class Member(SQLModel, table=True):
§     id: int | None = Field(default=None, primary_key=True)
§     team_id: int | None = Field(default=None, foreign_key="team.id")
§ engine = create_engine("sqlite://")
from sqlalchemy import event

@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, record):
    connection.execute("PRAGMA foreign_keys=ON")
§ SQLModel.metadata.create_all(engine)
§ with Session(engine) as session:
§     session.add(Member(team_id=99))
§     try:
§         session.commit()
§         print("没有检查")
§     except IntegrityError:
§         print("外键约束生效")  # => 外键约束生效
```

## 修改表结构 {#migrations}

`create_all` 只创建不存在的表，不会修改已有的表。给 `Task` 加一个字段后，数据库里的表不会跟着变，这时候要用 Alembic，它的作用相当于 Java 的 Flyway 或 Room 的 `Migration`。

```bash
pip install alembic
alembic init migrations
```

第一次使用要改三个地方：

1. 在 `alembic.ini` 里把 `sqlalchemy.url` 改成 `sqlite:///app.db`。
2. 在 `migrations/env.py` 里导入模型，设置 `target_metadata = SQLModel.metadata`，并给在线和离线两处 `context.configure()` 都加上 `render_as_batch=True`。SQLite 的 `ALTER` 功能很有限，开启后 Alembic 能用重建表的方式完成修改。
3. 在 `migrations/script.py.mako` 里加一行 `import sqlmodel`。SQLModel 的字段类型会写进迁移文件，少了这一行，迁移运行时会报 `NameError`。

之后每次修改模型，都生成并执行一次迁移：

```bash
alembic revision --autogenerate -m "add priority"
alembic upgrade head     # 升级到最新版本
alembic downgrade -1     # 回退一个版本
```

:::compare 给表加一列
```python no-run
def upgrade() -> None:
    with op.batch_alter_table("task") as batch_op:
        batch_op.add_column(sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ))

def downgrade() -> None:
    with op.batch_alter_table("task") as batch_op:
        batch_op.drop_column("priority")
```
```java no-run
public class V2__AddPriority extends BaseJavaMigration {
    @Override
    public void migrate(Context context) throws Exception {
        try (var statement = context.getConnection().createStatement()) {
            statement.execute("ALTER TABLE task ADD COLUMN "
                + "priority INTEGER NOT NULL DEFAULT 0");
        }
    }
}
```
```kotlin no-run
val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL(
            "ALTER TABLE task ADD COLUMN " +
                "priority INTEGER NOT NULL DEFAULT 0"
        )
    }
}

val db = Room.databaseBuilder(
    context,
    AppDatabase::class.java,
    "app.db",
).addMigrations(MIGRATION_1_2).build()
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 版本记录 | 每个迁移一个文件，用哈希串成链 | 类名或文件名里的版本号 | `@Database` 的整数版本号 |
| 自动生成 | `--autogenerate` 对比模型和数据库 | 不生成，自己写 | `@AutoMigration` |
| 执行时机 | 部署时运行 `alembic upgrade head` | 应用启动时自动执行 | 打开数据库时自动执行 |
| 回退 | 写在 `downgrade` 里 | 通常写一个新迁移来修正 | 单独写一个 `Migration(2, 1)` |

> 要点: 自动生成的迁移一定要检查。给已有数据的表加非空列时，要手动加上 `server_default`，否则升级会失败。
:::

## 并发写入 {#concurrency}

SQLite 允许多个连接同时读，但同一时刻只能有一个连接写，其他写入要排队，等太久会报 `database is locked`。两个设置能缓解这个问题：

- **WAL 模式**：读和写互不阻塞。Room 在大多数设备上默认开启，SQLModel 要自己设置。
- **`timeout`**：拿不到写锁时最多等多久，Python 默认 5 秒。

```python
§ from sqlalchemy import event
§ from sqlmodel import create_engine
engine = create_engine(
    "sqlite:///app.db",
    connect_args={"check_same_thread": False, "timeout": 30},
)

@event.listens_for(engine, "connect")
def configure_sqlite(connection, record):
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
§ with engine.connect() as connection:
§     pass
```

SQLite 文件不能在多台机器之间共享。服务要部署多个实例，或者写入并发很高时，就该换成 Postgres。

:::warn 流式接口里不要用 SessionDep
依赖项要到响应结束才清理，SSE 接口用 `SessionDep` 的话，连接会被占用到流结束。大模型的回答可能要生成几十秒，这样做很浪费。另外 `Session` 是阻塞的，不能直接在 `async def` 里调用。

正确的做法是在生成完之后，用 `run_in_threadpool` 把写入放到线程池里，并且只在写入时打开 `Session`。
:::

```python
§ from collections.abc import AsyncIterable
§ from fastapi import FastAPI
§ from fastapi.sse import EventSourceResponse, ServerSentEvent
§ from fastapi.testclient import TestClient
§ from sqlmodel import Field, Session, SQLModel, create_engine, select
§ from sqlalchemy.pool import StaticPool
§ engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
§ class Message(SQLModel, table=True):
§     id: int | None = Field(default=None, primary_key=True)
§     text: str
§ SQLModel.metadata.create_all(engine)
§ app = FastAPI()
§ async def call_model() -> AsyncIterable[str]:
§     yield "Hello"
§     yield ", world"
from fastapi.concurrency import run_in_threadpool

def save_answer(text: str) -> None:
    with Session(engine) as session:
        session.add(Message(text=text))
        session.commit()

@app.post("/chat", response_class=EventSourceResponse)
async def chat() -> AsyncIterable[ServerSentEvent]:
    answer = ""
    async for delta in call_model():
        answer += delta
        yield ServerSentEvent(data={"text": delta}, event="delta")
    await run_in_threadpool(save_answer, answer)
§ TestClient(app).post("/chat")
§ with Session(engine) as session:
§     print(session.exec(select(Message)).one().text)  # => Hello, world
```

:::map SQLModel、JPA 和 Room 写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `class Task(SQLModel, table=True)` | `@Entity` | `@Entity` | 一个类同时是表和数据模型 |
| `create_engine()` | `DataSource` | `Room.databaseBuilder()` | 整个应用只创建一次 |
| `Session` | `EntityManager` | `@Dao` | `Session` 和 `EntityManager` 都跟踪对象的改动 |
| `select(Task).where()` | JPQL | `@Query` | Room 在编译时检查 SQL |
| `session.commit()` | `@Transactional` | 自动提交 | 忘记 `commit` 不会保存 |
| `Relationship` | `@OneToMany` | `@Relation` | 前两个默认在访问时才查询 |
| Alembic | Flyway | `Migration` | Alembic 能对比模型生成迁移 |
:::

:::recap
- SQLite 就是一个文件，Python 用 `sqlite3` 或 SQLModel 访问，占位符一律用 `?`
- `table=True` 的类对应数据库表，API 的入参和出参用单独的模型
- 改动在 `commit` 时才保存，`engine` 全局一个，`Session` 每次请求一个
- `Session` 是阻塞的，接口写成 `def`，并设置 `check_same_thread=False`
- SQLite 默认不检查外键，WAL 和 `timeout` 要自己配置
- `create_all` 不会修改已有的表，改结构用 Alembic，并检查自动生成的迁移
- 流式接口不要用 `SessionDep`，生成完再用 `run_in_threadpool` 写入
:::
