---
id: postgres
part: 数据存储
title: Postgres 和数据库迁移
lede: SQLite 撑不住多实例和高并发写入时，就该换 Postgres。代码改动很小，要注意的是类型、连接池和上线时的迁移顺序。
source: PostgreSQL JSON 类型 | https://www.postgresql.org/docs/current/datatype-json.html ; 显式锁 | https://www.postgresql.org/docs/current/explicit-locking.html ; Psycopg 3 | https://www.psycopg.org/psycopg3/docs/ ; SQLAlchemy 连接池 | https://docs.sqlalchemy.org/en/20/core/pooling.html ; Alembic 自动生成 | https://alembic.sqlalchemy.org/en/latest/autogenerate.html ; Alembic 操作参考 | https://alembic.sqlalchemy.org/en/latest/ops.html
versions: PostgreSQL 18 · Psycopg 3.3 · SQLAlchemy 2.1 · Alembic 1.20 · Spring Boot 4.1
seo_title: FastAPI 接入 PostgreSQL：连接池、JSONB 和 Alembic
seo_description: 从 SQLite 迁移到 PostgreSQL：SQLModel 连接配置、连接池、类型差异、JSONB、upsert、行锁和 Alembic 上线流程，并和 Spring Boot、Hikari、JPA 对比。
---

## 什么时候换 Postgres {#when}

SQLite 适合单机、写入不多的服务。出现下面任何一种情况，就该换成 Postgres：

- 服务要部署多个实例，它们不能共用一个 SQLite 文件
- 写入并发高，经常出现 `database is locked`
- 需要 `JSONB` 查询、全文检索或向量检索这类能力

SQLModel 和 SQLAlchemy 屏蔽了大部分差异，换数据库主要是换连接地址。Android 应用不会直接连接服务端数据库，所以这一章的 Kotlin 示例是服务端写法，和 Java 一样基于 Spring。

本地用 Docker 启动一个就够了：

```bash
docker run --name pg -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres:18
```

Python 这边要安装驱动。`binary` 附带了编译好的 C 库，不用在系统里安装 libpq。

```bash
pip install "psycopg[binary]"
```

## 连接数据库 {#connect}

连接地址的开头写 `postgresql+psycopg`，表示用 Psycopg 3 驱动。其余代码和 SQLite 相同。

Postgres 的每个连接都对应服务端的一个进程，创建成本比较高，所以要用连接池。SQLAlchemy 默认已经有连接池，下面这几个参数常要调整。

:::compare 配置连接池
```python
§ import tempfile
§ import pgserver
§ server = pgserver.get_server(tempfile.mkdtemp())
from sqlalchemy import text
from sqlmodel import create_engine

DATABASE_URL = "postgresql+psycopg://postgres:secret@localhost:5432/postgres"
§ DATABASE_URL = server.get_uri().replace("postgresql://", "postgresql+psycopg://")

engine = create_engine(
    DATABASE_URL,
    pool_size=5,         # 保持的连接数
    max_overflow=10,     # 高峰时最多多开几个
    pool_pre_ping=True,  # 使用前检查连接是否还活着
)

with engine.connect() as connection:
    print(connection.scalar(text("SELECT 1 + 1")))  # => 2
§ engine.dispose()
§ server.cleanup()
```
```java no-run
§ import com.zaxxer.hikari.*;
§ import javax.sql.DataSource;
§ import org.springframework.context.annotation.Bean;
@Bean
DataSource dataSource() {
    var config = new HikariConfig();
    config.setJdbcUrl("jdbc:postgresql://localhost:5432/postgres");
    config.setUsername("postgres");
    config.setPassword("secret");
    config.setMaximumPoolSize(15);
    return new HikariDataSource(config);
}
```
```kotlin no-run
§ import com.zaxxer.hikari.HikariConfig
§ import com.zaxxer.hikari.HikariDataSource
§ import javax.sql.DataSource
§ import org.springframework.context.annotation.Bean
@Bean
fun dataSource(): DataSource = HikariDataSource(
    HikariConfig().apply {
        jdbcUrl = "jdbc:postgresql://localhost:5432/postgres"
        username = "postgres"
        password = "secret"
        maximumPoolSize = 15
    },
)
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 连接池 | SQLAlchemy 自带 | HikariCP | HikariCP |
| 最大连接数 | `pool_size + max_overflow` | `maximumPoolSize` | `maximumPoolSize` |
| 检查失效连接 | `pool_pre_ping=True` | 默认检查 | 默认检查 |

> 要点: 多个实例的连接数要加起来算。Postgres 的 `max_connections` 默认只有 100，四个实例各开 30 个就超了。
:::

每个请求一个 `Session`、接口写成 `def` 的做法和 SQLite 一样。`check_same_thread` 是 SQLite 的参数，换成 Postgres 后要删掉。

## 和 SQLite 的差异 {#diff}

SQLite 对类型很宽松，往整数列写字符串也能成功。Postgres 会直接报错，这些问题常在换库时才暴露。

| 方面 | SQLite | Postgres |
| --- | --- | --- |
| 类型检查 | 宽松，整数列能存字符串 | 严格，类型不对就报错 |
| 外键 | 默认不检查 | 始终检查 |
| 并发写入 | 同一时刻只有一个写入者 | 多个事务同时写，只有同一行才排队 |
| 修改表结构 | `ALTER` 功能很少，要重建表 | 功能完整，大部分操作在事务里 |
| JSON | 存成文本 | `JSONB` 可以建索引 |
| 字符串比较 | `LIKE` 对英文不区分大小写 | 区分，不区分时用 `ILIKE` |

开发环境也用 Postgres，不要开发用 SQLite、线上用 Postgres。两边的差异会让问题只在线上出现。

## 存 JSON {#jsonb}

Agent 应用常要保存结构不固定的数据，比如工具调用的参数。Postgres 的 `JSONB` 把 JSON 解析后存储，可以查询内部字段，也能建索引。

:::compare JSONB 字段
```python
§ import tempfile
§ import pgserver
§ server = pgserver.get_server(tempfile.mkdtemp())
§ DATABASE_URL = server.get_uri().replace("postgresql://", "postgresql+psycopg://")
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel, create_engine, select

class ToolCall(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    arguments: dict = Field(default_factory=dict, sa_column=Column(JSONB))

engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    session.add(ToolCall(name="weather", arguments={"city": "北京"}))
    session.commit()

    query = select(ToolCall).where(ToolCall.arguments["city"].astext == "北京")
    print(session.exec(query).one().arguments)  # => {'city': '北京'}
§ engine.dispose()
§ server.cleanup()
```
```java no-run
§ import org.hibernate.annotations.JdbcTypeCode;
§ import org.hibernate.type.SqlTypes;
@Entity
class ToolCall {
    @Id @GeneratedValue Long id;
    String name;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    Map<String, Object> arguments;
}

interface ToolCallRepository extends JpaRepository<ToolCall, Long> {
    @Query(value = "SELECT * FROM tool_call "
        + "WHERE arguments ->> 'city' = :city", nativeQuery = true)
    List<ToolCall> findByCity(String city);
}
```
```kotlin no-run
§ import jakarta.persistence.*
§ import org.hibernate.annotations.JdbcTypeCode
§ import org.hibernate.type.SqlTypes
§ import org.springframework.data.jpa.repository.JpaRepository
§ import org.springframework.data.jpa.repository.Query
@Entity
class ToolCall(
    @Id @GeneratedValue var id: Long? = null,
    var name: String = "",

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    var arguments: Map<String, Any> = emptyMap(),
)

interface ToolCallRepository : JpaRepository<ToolCall, Long> {
    @Query(
        "SELECT * FROM tool_call WHERE arguments ->> 'city' = :city",
        nativeQuery = true,
    )
    fun findByCity(city: String): List<ToolCall>
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 字段声明 | `sa_column=Column(JSONB)` | `@JdbcTypeCode(SqlTypes.JSON)` | `@JdbcTypeCode(SqlTypes.JSON)` |
| 读出来的类型 | `dict` | `Map` | `Map` |
| 查询内部字段 | `字段["city"].astext` | 原生 SQL 的 `->>` | 原生 SQL 的 `->>` |

> 要点: 字段是 `dict` 时，直接改字典内容不会被 `Session` 发现。要重新赋值，或者用 SQLAlchemy 的 `MutableDict`。
:::

## 并发写入 {#concurrency}

多个请求同时修改同一行时，容易出现「先读后写」的丢失更新。两个请求都读到余额 100，各扣 30，最后余额是 70，而不是 40。

有两种常用的解决办法：

- **行锁**：`SELECT ... FOR UPDATE` 读取时锁住这一行，其他事务要等当前事务结束
- **原子更新**：一条 SQL 直接完成，比如 `UPDATE ... SET n = n - 30`

:::compare 行锁
```python
§ import tempfile
§ import pgserver
§ server = pgserver.get_server(tempfile.mkdtemp())
§ DATABASE_URL = server.get_uri().replace("postgresql://", "postgresql+psycopg://")
from sqlmodel import Field, Session, SQLModel, create_engine, select

class Account(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    balance: int

engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)
with Session(engine) as session:
    session.add(Account(id=1, balance=100))
    session.commit()

def withdraw(session: Session, account_id: int, amount: int) -> int:
    query = select(Account).where(Account.id == account_id).with_for_update()
    account = session.exec(query).one()
    account.balance -= amount
    session.commit()
    return account.balance

with Session(engine) as session:
    print(withdraw(session, 1, 30))  # => 70
§ engine.dispose()
§ server.cleanup()
```
```java no-run
§ @Entity class Account { @Id Long id; int balance; }
interface AccountRepository extends JpaRepository<Account, Long> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from Account a where a.id = :id")
    Account findForUpdate(long id);
}

@Transactional
int withdraw(AccountRepository accounts, long id, int amount) {
    var account = accounts.findForUpdate(id);
    account.balance -= amount;
    return account.balance;
}
```
```kotlin no-run
§ import jakarta.persistence.Entity
§ import jakarta.persistence.Id
§ import jakarta.persistence.LockModeType
§ import org.springframework.data.jpa.repository.JpaRepository
§ import org.springframework.data.jpa.repository.Lock
§ import org.springframework.data.jpa.repository.Query
§ import org.springframework.transaction.annotation.Transactional
§ @Entity class Account(@Id var id: Long = 0, var balance: Int = 0)
interface AccountRepository : JpaRepository<Account, Long> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from Account a where a.id = :id")
    fun findForUpdate(id: Long): Account
}

@Transactional
fun withdraw(accounts: AccountRepository, id: Long, amount: Int): Int {
    val account = accounts.findForUpdate(id)
    account.balance -= amount
    return account.balance
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 加行锁 | `.with_for_update()` | `@Lock(PESSIMISTIC_WRITE)` | `@Lock(PESSIMISTIC_WRITE)` |
| 释放 | `commit` 或回滚时 | 事务结束时 | 事务结束时 |

> 要点: 事务要尽量短，不要在持有行锁时调用大模型。一次调用几十秒，这一行就被锁住几十秒。
:::

「有就更新，没有就插入」用 `ON CONFLICT`，一条语句完成，不会有竞争。

```python
§ import tempfile
§ import pgserver
§ server = pgserver.get_server(tempfile.mkdtemp())
§ DATABASE_URL = server.get_uri().replace("postgresql://", "postgresql+psycopg://")
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Field, Session, SQLModel, create_engine, select

class Usage(SQLModel, table=True):
    user_id: str = Field(primary_key=True)
    tokens: int = 0

engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)

def add_tokens(session: Session, user_id: str, tokens: int) -> None:
    statement = insert(Usage).values(user_id=user_id, tokens=tokens)
    session.exec(statement.on_conflict_do_update(
        index_elements=["user_id"],
        set_={"tokens": Usage.tokens + tokens},
    ))
    session.commit()

with Session(engine) as session:
    add_tokens(session, "ada", 10)
    add_tokens(session, "ada", 5)
    print(session.exec(select(Usage)).one().tokens)  # => 15
§ engine.dispose()
§ server.cleanup()
```

## 迁移怎么上线 {#migrations}

「SQLite 与 SQLModel」一章讲了 Alembic 的基本用法。换成 Postgres 后，`render_as_batch` 可以关掉，上线时要多注意几件事。

**密码不要写进 `alembic.ini`。** 在 `migrations/env.py` 里从环境变量读取：

```python no-run
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
```

**先看再执行。** 这几个命令适合放进发布流程：

```bash
alembic upgrade head --sql   # 只输出 SQL，不执行
alembic current              # 数据库当前的版本
alembic check                # 模型和迁移不一致时报错，适合放进 CI
```

**新旧代码要能同时运行。** 滚动发布时，新旧两个版本的服务同时连着数据库，所以破坏性修改不能一步完成。比如把 `name` 改成 `title`，要分三次发布：

1. 新增 `title` 列，代码同时写两列，再把旧数据复制过来
2. 代码改成只读写 `title`
3. 删除 `name` 列

**注意锁。** `ALTER TABLE` 大多需要表上最强的锁，等待期间后面的查询全部排队。给迁移设置 `lock_timeout`，等不到锁就失败，再找时间重试。大表上建索引要用 `CONCURRENTLY`，它不能放在事务里，所以要包一层 `autocommit_block`：

```python no-run
def upgrade() -> None:
    op.execute("SET lock_timeout = '5s'")
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_message_user_id",
            "message",
            ["user_id"],
            postgresql_concurrently=True,
        )
```

:::compare 迁移工具
```python no-run
# alembic upgrade head
def upgrade() -> None:
    op.add_column("task", sa.Column("priority", sa.Integer(), server_default="0"))

def downgrade() -> None:
    op.drop_column("task", "priority")
```
```java no-run
public class V3__AddPriority extends BaseJavaMigration {
    @Override
    public void migrate(Context context) throws Exception {
        try (var statement = context.getConnection().createStatement()) {
            statement.execute(
                "ALTER TABLE task ADD COLUMN priority INT DEFAULT 0");
        }
    }
}
```
```kotlin no-run
§ import org.flywaydb.core.api.migration.BaseJavaMigration
§ import org.flywaydb.core.api.migration.Context
class V3__AddPriority : BaseJavaMigration() {
    override fun migrate(context: Context) {
        context.connection.createStatement().use { statement ->
            statement.execute(
                "ALTER TABLE task ADD COLUMN priority INT DEFAULT 0",
            )
        }
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 工具 | Alembic | Flyway | Flyway |
| 生成 | 对比模型自动生成，再人工检查 | 自己写 | 自己写 |
| 触发 | 单独运行命令 | 默认在应用启动时运行 | 默认在应用启动时运行 |
| 多实例 | 发布流程里只运行一次 | 用数据库锁保证只有一个实例执行 | 用数据库锁保证只有一个实例执行 |

> 要点: 不要在每个实例启动时运行 `alembic upgrade head`。多个实例同时迁移会互相冲突，「用 Docker 部署」一章用单独的任务完成这一步。
:::

:::more 异步驱动
`create_async_engine` 配合 `postgresql+psycopg` 或 `asyncpg` 可以在 `async def` 接口里访问数据库。代价是所有数据库代码都要写 `await`，访问关联属性也不能再隐式触发查询。

大多数服务用同步 `Session` 配 `def` 接口就够了。只有并发连接很多、数据库操作又很频繁时再考虑换成异步。
:::

:::map 服务端数据库写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `postgresql+psycopg://...` | `jdbc:postgresql://...` | `jdbc:postgresql://...` | 连接地址 |
| `create_engine(pool_size=5)` | HikariCP | HikariCP | 都要限制连接数 |
| `Column(JSONB)` | `@JdbcTypeCode(SqlTypes.JSON)` | `@JdbcTypeCode(SqlTypes.JSON)` | 可查询的 JSON |
| `.with_for_update()` | `@Lock(PESSIMISTIC_WRITE)` | `@Lock(PESSIMISTIC_WRITE)` | 行锁 |
| `on_conflict_do_update` | 原生 SQL | 原生 SQL | 一条语句完成 upsert |
| Alembic | Flyway | Flyway | Flyway 默认随应用启动 |
:::

:::recap
- 多实例、高并发写入或需要 `JSONB` 时换 Postgres，开发环境也用它
- 连接地址换成 `postgresql+psycopg`，删掉 `check_same_thread`
- 配好连接池，所有实例的连接数加起来不能超过 `max_connections`
- 先读后写要加行锁或改成原子更新，事务里不要调用大模型
- 破坏性迁移分多次发布，让新旧代码能同时运行
- 迁移时设置 `lock_timeout`，大表索引用 `CONCURRENTLY`，只由一个任务执行迁移
:::
