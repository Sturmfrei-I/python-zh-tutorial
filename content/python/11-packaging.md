---
id: virtual-environments
part: 工程实践
title: 虚拟环境与依赖
lede: 每个项目都要有自己的虚拟环境。venv 加 pip 相当于一个极简的 Maven。最后再看看学完之后往哪走。
source: 虚拟环境和包 | venv.html ; 接下来 | whatnow.html
seo_title: Python 虚拟环境与 pip：对比 Maven 和 Gradle
seo_description: 讲解 Python 虚拟环境 venv、pip、requirements.txt、pyproject.toml 和 uv，并和 Maven、Gradle 对比，最后给出 Python 常用框架和学习方向。
---

## 为什么需要虚拟环境 {#why}

Maven 把不同版本的 jar 都存在 `~/.m2`，每个项目通过类路径选用自己的版本，多个版本可以共存。

Python 的 `import` 只看 `site-packages` 目录，同一个包在目录里只能有一个版本。A 项目要 `requests 2.31`，B 项目要 `requests 2.20`，装在同一个地方就会冲突。虚拟环境给每个项目一份独立的 `site-packages`，问题就解决了。

## 创建和激活 {#venv}

```bash
python3 -m venv .venv            # 在项目目录创建虚拟环境
source .venv/bin/activate        # macOS / Linux 激活
.venv\Scripts\activate           # Windows 激活
python --version                 # 现在 python 指向虚拟环境
deactivate                       # 退出
```

激活只是修改当前终端的 `PATH`，让 `python` 和 `pip` 指向 `.venv` 里的版本。csh 和 fish 分别用 `activate.csh` 和 `activate.fish`。IDE 会自动识别 `.venv`。把 `.venv/` 写进 `.gitignore`，不要提交它。

## pip 和依赖文件 {#pip}

虚拟环境激活之后，`pip` 把包装进项目自己的 `site-packages`。

```bash
pip install requests             # 安装最新版
pip install "requests==2.32.3"   # 安装指定版本
pip install -U requests          # 升级
pip uninstall requests           # 卸载
pip list                         # 列出已安装的包
pip show requests                # 查看某个包的信息
pip freeze > requirements.txt    # 导出当前环境的精确版本
pip install -r requirements.txt  # 按文件安装
```

不确定 `pip` 指向哪个 Python 时，写 `python3 -m pip install requests` 最稳妥，这样包一定会装到这个解释器下面。

:::compare 声明依赖
```python:text
# requirements.txt
requests==2.32.3
rich>=13.0
```
```java:xml
<!-- pom.xml -->
<dependency>
  <groupId>com.squareup.okhttp3</groupId>
  <artifactId>okhttp</artifactId>
  <version>4.12.0</version>
</dependency>
```
```kotlin no-run
// build.gradle.kts
dependencies {
    implementation(
        "com.squareup.okhttp3:okhttp:4.12.0"
    )
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 依赖文件 | `requirements.txt` | `pom.xml` | `build.gradle.kts` |
| 文件格式 | 每行一个包 | XML | Kotlin 脚本 |
| 包的标识 | 包名 | groupId + artifactId | `group:artifact` |
| 工具职责 | 只管安装 | 构建、测试、打包全管 | 构建、测试、打包全管 |

> 要点: 把依赖文件提交到版本库。别人克隆后执行创建虚拟环境和 `pip install -r` 两步就能运行。`pip freeze` 会把间接依赖也写进去，作用类似锁文件。
:::

:::map 工具对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `pip` | Maven | Gradle | Python 这边只管安装 |
| PyPI | Maven Central | Maven Central | 公共仓库 |
| `requirements.txt` | `pom.xml` 的依赖部分 | `build.gradle.kts` 的依赖部分 | |
| `pyproject.toml` | `pom.xml` | `build.gradle.kts` | 项目元数据和构建配置 |
| `.venv/` | 类路径 | 类路径 | 项目的依赖隔离 |
| `.whl` 文件 | `.jar` | `.jar` | 分发格式 |
| `pip freeze` | `mvn dependency:list` | `gradle dependencies` | 查看实际版本 |
:::

## 更现代的工具 {#tools}

官方教程只讲了 `venv` 和 `pip`，这是所有 Python 环境都有的基础。新项目可以考虑 `uv`，它把创建环境、管理依赖、锁定版本和运行程序合成了一套命令，使用体验接近 Gradle。

```bash
uv init demo          # 创建项目，生成 pyproject.toml
cd demo
uv add requests       # 添加依赖，同时更新锁文件
uv run main.py        # 在项目环境里运行，环境不存在时自动创建
```

## 下一步 {#next}

教程到这里就结束了。官方文档里最值得收藏的是下面这些。

- [标准库参考](https://docs.python.org/zh-cn/3.12/library/index.html)：查 API 最常用的文档
- [语言参考](https://docs.python.org/zh-cn/3.12/reference/index.html)：语法的严格定义
- [常见问题](https://docs.python.org/zh-cn/3.12/faq/index.html)：很多「为什么这样设计」都能在这里找到答案
- [PyPI](https://pypi.org/)：第三方包仓库

下面这张表列出了常见领域的主流库，帮你在 Python 生态里找到熟悉的位置。

:::map 生态对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| FastAPI | Spring Boot | Ktor | Web 接口 |
| Django | Spring MVC + JPA | Spring Boot | 全功能 Web 框架 |
| SQLAlchemy | Hibernate | Exposed | ORM |
| pydantic | Bean Validation + Jackson | kotlinx.serialization | 数据校验和序列化 |
| pytest | JUnit | Kotest | 测试 |
| asyncio | `CompletableFuture` | 协程 | 异步编程 |
| ruff | Checkstyle、Spotless | ktlint | 代码检查和格式化 |
| mypy、pyright | javac | kotlinc | 类型检查 |
| pandas、NumPy | Tablesaw | Kotlin DataFrame | 数据分析 |
| PyTorch | DJL | KotlinDL | 机器学习 |
:::

:::recap
- 每个项目一个虚拟环境：`python3 -m venv .venv`，再 `source .venv/bin/activate`
- `.venv/` 不提交，依赖文件要提交
- `pip freeze > requirements.txt` 导出版本，`pip install -r` 复现环境
- `pyproject.toml` 是现代项目的配置文件，相当于 `pom.xml`
- 新项目可以用 `uv` 代替 `venv` 加 `pip`
- 想写接口先学 FastAPI，想做数据先学 pandas
:::
