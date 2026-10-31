---
id: docker
part: 测试与部署
title: 用 Docker 部署
lede: 把服务和它依赖的一切打成镜像，在哪都能以同样的方式运行。这一章把 FastAPI、Postgres 和数据库迁移用 Compose 组合起来。
source: Docker 镜像概念 | https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/ ; Dockerfile 参考 | https://docs.docker.com/reference/dockerfile/ ; Docker Compose | https://docs.docker.com/compose/ ; Compose 启动顺序 | https://docs.docker.com/compose/how-tos/startup-order/ ; FastAPI 容器部署 | https://fastapi.tiangolo.com/zh/deployment/docker/
versions: Docker Compose V2 · Python 3.12 · PostgreSQL 18 · FastAPI 0.162
seo_title: FastAPI Docker 部署教程：Compose、Postgres 和迁移
seo_description: 用 Docker 部署 FastAPI：编写 Dockerfile、利用层缓存、非 root 运行、健康检查、用 Compose 编排 Postgres 和 Alembic 迁移，并和 Java jar 的部署方式对比。
---

## 镜像和容器 {#concepts}

镜像是打包好的只读文件系统，包含运行环境、依赖和代码。容器是镜像运行起来的实例。一个镜像可以启动很多个容器，关系类似类和对象。

Java 服务部署时只要目标机器有 JRE，一个 jar 就能运行。Python 没有这样的单文件产物，运行时要解释器和所有依赖都在位，所以容器几乎是 Python 服务的标准部署方式。

:::map 部署概念对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `python:3.12-slim` 镜像 | `eclipse-temurin:21-jre` 镜像 | `eclipse-temurin:21-jre` 镜像 | 基础运行环境 |
| `requirements.txt` | `pom.xml` | `build.gradle.kts` | 依赖清单 |
| `pip install` | `mvn package` | `gradle bootJar` | 构建步骤 |
| 源代码文件 | 打包好的 jar | 打包好的 jar | Python 直接复制源代码 |
| `fastapi run` | `java -jar app.jar` | `java -jar app.jar` | 启动命令 |
:::

## 写 Dockerfile {#dockerfile}

下面是一个 FastAPI 服务的 Dockerfile，项目结构是 `app/main.py` 加根目录的 `requirements.txt`。

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
```

几个写法都有原因：

- **`slim` 镜像**：比完整镜像小得多，Psycopg 用 `binary` 版本时不需要系统里的编译工具。
- **先复制 `requirements.txt`**：Docker 按层缓存，某一层的输入变了，它后面的层都要重新构建。依赖放在代码前面，只改代码时不用重新安装依赖。
- **`PYTHONUNBUFFERED=1`**：日志立刻输出，容器崩溃时不会丢失最后几行。
- **`USER appuser`**：不用 root 运行，服务被攻破时影响更小。
- **`CMD` 用列表写法**：程序是容器的 1 号进程，能直接收到停止信号，优雅退出。写成字符串时外面会多一层 `sh`，信号传不到程序。

Java 的 Dockerfile 结构相同，构建产物是一个 jar，所以常用多阶段构建，把构建工具留在第一阶段：

```dockerfile
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY . .
RUN ./gradlew bootJar

FROM eclipse-temurin:21-jre
COPY --from=build /src/build/libs/app.jar /app.jar
USER 1000
EXPOSE 8000
CMD ["java", "-jar", "/app.jar"]
```

## 排除文件 {#ignore}

`COPY` 之前，Docker 会把构建目录发给构建器。`.dockerignore` 排除不需要的文件，既能加快构建，也能防止密钥进入镜像。

```text
.git
.venv
__pycache__
*.pyc
.env
tests
```

:::warn 密钥不要进镜像
`.env` 一定要排除。镜像的每一层都能被读取，即使后面的 `RUN` 删除了文件，它在前面的层里还在。密钥只在运行时通过环境变量传入。
:::

## 构建和运行 {#run}

```bash
docker build -t my-api .
docker run --rm -p 8000:8000 --env-file .env my-api
```

`-p 8000:8000` 把主机端口映射到容器端口，`--env-file` 传入环境变量，`--rm` 表示退出后删除容器。

这几个命令查问题时最常用：

```bash
docker ps                    # 正在运行的容器
docker logs -f 容器名         # 查看日志
docker exec -it 容器名 bash   # 进入容器
docker compose down -v       # 停止并删除容器和数据卷
```

## 健康检查 {#health}

负载均衡和容器平台要靠一个接口判断服务是否正常。一般分成两个：

- **存活检查**：进程还在运行就返回 200，失败时重启容器。
- **就绪检查**：依赖也都正常才返回 200，失败时暂停分发流量。

:::compare 健康检查接口
```python
from fastapi import FastAPI, Response, status
from fastapi.testclient import TestClient

app = FastAPI()
database_ok = True

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.get("/health/ready")
def ready(response: Response):
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ok"}

client = TestClient(app)
client.get("/health/ready").status_code  # => 200
```
```java no-run
// 引入 spring-boot-starter-actuator 后自动提供
// GET /actuator/health/liveness
// GET /actuator/health/readiness
@Component
class DatabaseHealth implements HealthIndicator {
    private final DataSource dataSource;

    DatabaseHealth(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Health health() {
        try (var connection = dataSource.getConnection()) {
            return Health.up().build();
        } catch (SQLException e) {
            return Health.down(e).build();
        }
    }
}
§ interface HealthIndicator { Health health(); }
§ static class Health {
§     static Health up() { return null; }
§     static Health down(Exception e) { return null; }
§     Health build() { return this; }
§ }
§ interface DataSource { Connection getConnection() throws SQLException; }
```
```kotlin no-run
§ import java.sql.Connection
§ import java.sql.SQLException
§ import org.springframework.stereotype.Component
§ interface HealthIndicator { fun health(): Health }
§ class Health {
§     companion object {
§         fun up() = Health()
§         fun down(e: Exception) = Health()
§     }
§     fun build() = this
§ }
§ interface DataSource { val connection: Connection }
// 引入 spring-boot-starter-actuator 后自动提供
// GET /actuator/health/liveness
// GET /actuator/health/readiness
@Component
class DatabaseHealth(
    private val dataSource: DataSource,
) : HealthIndicator {
    override fun health(): Health = try {
        dataSource.connection.use { Health.up().build() }
    } catch (e: SQLException) {
        Health.down(e).build()
    }
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 实现 | 自己写两个接口 | Actuator 自带 | Actuator 自带 |
| 依赖检查 | 自己写 | 实现 `HealthIndicator` | 实现 `HealthIndicator` |

> 要点: 存活检查不要依赖数据库。数据库一抖动，所有容器都会被重启，问题反而更严重。
:::

## 用 Compose 组合服务 {#compose}

服务、数据库和迁移任务都写进 `compose.yaml`，一条命令全部启动。下面的配置有三个服务，启动顺序由 `depends_on` 决定：

```yaml
services:
  db:
    image: postgres:18
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: app
    volumes:
      - db-data:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 3s
      retries: 10

  migrate:
    build: .
    command: alembic upgrade head
    environment:
      DATABASE_URL: postgresql+psycopg://app:${POSTGRES_PASSWORD}@db:5432/app
    depends_on:
      db:
        condition: service_healthy

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg://app:${POSTGRES_PASSWORD}@db:5432/app
    depends_on:
      migrate:
        condition: service_completed_successfully

volumes:
  db-data:
```

把密码写进同目录的 `.env`，Compose 会自动读取并替换 `${POSTGRES_PASSWORD}`。

```bash
echo "POSTGRES_PASSWORD=secret" > .env
docker compose up --build
```

这份配置有三点要注意：

- **服务名就是主机名。** `api` 用 `db:5432` 访问数据库。容器里的 `localhost` 指向容器自己，不是主机。
- **`service_healthy` 等数据库就绪。** 只写服务名的话，Compose 等容器启动就算完成，而数据库此时可能还不能连接。
- **`migrate` 运行一次就退出。** `service_completed_successfully` 保证迁移成功后才启动 `api`。这样迁移只执行一次，不会多个实例同时执行。

数据写在 `db-data` 这个数据卷里，删除容器不会丢失，`docker compose down -v` 才会删除。

:::warn Postgres 18 的数据目录变了
从 18 版开始，官方镜像的数据卷要挂载到 `/var/lib/postgresql`。网上很多旧配置挂载的是 `/var/lib/postgresql/data`，在 18 上启动时会报错。
:::

## 上线前检查 {#checklist}

- **工作进程数。** `fastapi run --workers 4` 启动多个进程。一个 Python 进程同一时刻只有一个线程在执行字节码，CPU 多时要靠多进程。在 Kubernetes 上一般每个容器一个进程，由平台增加副本。
- **反向代理。** 前面有 Nginx 时，关闭 SSE 接口的缓冲，并把 `proxy_read_timeout` 调大，否则长时间生成的回答会被切断。
- **优雅退出。** 收到停止信号后，服务会等正在处理的请求结束。流式接口可能很久才结束，所以要限制等待时间，容器平台的终止宽限期也要配套调整。
- **日志。** 输出到标准输出，由平台收集，不要写进容器里的文件。
- **资源限制。** 给容器设置内存上限，Python 进程超出后会被杀掉，比拖垮整台机器好。

:::recap
- 镜像是打包好的文件系统，容器是运行中的实例
- 依赖放在代码前面复制，利用层缓存，用 `.dockerignore` 排除 `.env`
- 用非 root 用户运行，`CMD` 用列表写法，程序才能收到停止信号
- 存活检查不依赖数据库，就绪检查才检查依赖
- Compose 里用 `service_healthy` 等数据库，用一次性任务执行迁移
- 容器里访问数据库用服务名，不用 `localhost`
:::
