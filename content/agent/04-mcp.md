---
id: mcp
part: 连接外部能力
title: MCP 协议
lede: 每接一个工具都要写一遍适配代码，MCP 就是来解决这个问题的。工具写成 MCP Server，所有支持它的 Agent 都能直接用。
source: MCP 规范 | https://modelcontextprotocol.io/specification/latest ; MCP 简介 | https://modelcontextprotocol.io/docs/getting-started/intro ; MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk ; Python SDK v2 迁移指南 | https://py.sdk.modelcontextprotocol.io/v2/migration/ ; MCP Java SDK | https://github.com/modelcontextprotocol/java-sdk
versions: MCP 规范 2026-07-28 · MCP Python SDK 2.3 · MCP Java SDK 2.1
seo_title: MCP 协议教程：用 Python 开发 MCP Server 和 Client
seo_description: Agent 开发必备的 Model Context Protocol 入门：Host、Client、Server 架构，Tools、Resources、Prompts，用 MCPServer 开发服务，stdio 和 Streamable HTTP，接入 Agent 循环和安全注意事项。
---

## 为什么要有 MCP {#why}

假设有 5 个 Agent 应用和 10 个外部系统。没有统一标准时，每个应用都要给每个系统写一遍适配，一共 50 份代码。

MCP（Model Context Protocol）是一个开放协议，规定 Agent 应用和外部工具怎么对话。系统只要实现一次 MCP Server，应用只要实现一次 MCP Client，两边就都能互通。

写过 IDE 插件的话，这个思路来自 LSP：编辑器和语言服务器之间有统一协议，编辑器不用为每种语言单独适配。

## 架构 {#architecture}

MCP 里有三个角色：

- **Host**：Agent 应用本身，比如 Claude Code 或你写的程序
- **Client**：Host 里的连接器，每个连接对应一个 Server
- **Server**：提供能力的服务，可以是本地进程，也可以是远程服务

通信使用 JSON-RPC 2.0。Server 能提供三种能力，区别在于由谁决定使用：

| 能力 | 是什么 | 谁来决定 |
| --- | --- | --- |
| Tools | 可以执行的函数 | 模型 |
| Resources | 可以读取的数据，比如文件 | 应用 |
| Prompts | 提示词模板 | 用户 |

Tools 最常用，本章也以它为主。

## 写一个 Server {#server}

MCP 的 Python SDK 从 2.0 版起把 `FastMCP` 改名为 `MCPServer`，网上的旧教程要注意这个变化。用法没怎么变：函数加上装饰器就是工具，类型注解和文档字符串自动变成工具定义。

```bash
pip install mcp
```

:::compare 定义 MCP Server
```python
from mcp.server.mcpserver import MCPServer

server = MCPServer("weather")
§ server.run = lambda: None

@server.tool()
def get_weather(city: str) -> str:
    """查询城市当前的天气"""
    return f"{city}：晴，25 度"

if __name__ == "__main__":
    server.run()  # 默认用 stdio 通信
```
```java no-run
§ import io.modelcontextprotocol.json.McpJsonDefaults;
§ import io.modelcontextprotocol.server.McpServer;
§ import io.modelcontextprotocol.server.transport.StdioServerTransportProvider;
§ import io.modelcontextprotocol.spec.McpSchema;
void run() {
    var mapper = McpJsonDefaults.getMapper();
    var transport = new StdioServerTransportProvider(mapper);

    var tool = McpSchema.Tool.builder()
        .name("get_weather")
        .description("查询城市当前的天气")
        .inputSchema(mapper, """
            {"type": "object",
             "properties": {"city": {"type": "string"}},
             "required": ["city"]}
            """)
        .build();

    McpServer.sync(transport)
        .serverInfo("weather", "1.0.0")
        .toolCall(tool, (exchange, request) -> {
            var city = request.arguments().get("city");
            return McpSchema.CallToolResult.builder()
                .addTextContent(city + "：晴，25 度")
                .build();
        })
        .build();
}
```
```kotlin no-run
§ import io.modelcontextprotocol.json.McpJsonDefaults
§ import io.modelcontextprotocol.server.McpServer
§ import io.modelcontextprotocol.server.transport.StdioServerTransportProvider
§ import io.modelcontextprotocol.spec.McpSchema
fun run() {
    val mapper = McpJsonDefaults.getMapper()
    val transport = StdioServerTransportProvider(mapper)

    val tool = McpSchema.Tool.builder()
        .name("get_weather")
        .description("查询城市当前的天气")
        .inputSchema(
            mapper,
            """{"type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"]}""",
        )
        .build()

    McpServer.sync(transport)
        .serverInfo("weather", "1.0.0")
        .toolCall(tool) { _, request ->
            val city = request.arguments()["city"]
            McpSchema.CallToolResult.builder()
                .addTextContent("$city：晴，25 度")
                .build()
        }
        .build()
}
```

| 对比项 | python | java | kotlin |
| --- | --- | --- | --- |
| 声明工具 | 装饰器 | Builder 加回调 | Builder 加回调 |
| 输入 Schema | 从类型注解生成 | 手写或由框架生成 | 手写或由框架生成 |
| 取参数 | 函数参数 | `request.arguments()` | `request.arguments()` |

> 要点: Java 项目一般不直接用这个 Builder。Spring AI 提供了注解式的写法，体验和 Python 的装饰器接近。
:::

## 调用 Server {#client}

`Client` 负责连接和通信。直接把 `server` 对象传进去，就在同一个进程里通信，不用启动子进程，写测试时很方便。

```python
import asyncio

from mcp import Client
from mcp.server.mcpserver import MCPServer

server = MCPServer("weather")

@server.tool()
def get_weather(city: str) -> str:
    """查询城市当前的天气"""
    return f"{city}：晴"

async def main():
    async with Client(server) as client:
        result = await client.list_tools()
        tool = result.tools[0]
        print(tool.name)  # => get_weather
        print(tool.description)  # => 查询城市当前的天气
        print(tool.input_schema["required"])  # => ['city']

        answer = await client.call_tool("get_weather", {"city": "北京"})
        print(answer.content[0].text)  # => 北京：晴
        print(answer.is_error)  # => False

asyncio.run(main())
```

## 资源和提示 {#resources}

资源用网址形式的标识符，提示是可以带参数的模板。它们的写法和工具一样。

```python
import asyncio

from mcp import Client
from mcp.server.mcpserver import MCPServer

server = MCPServer("docs")

@server.resource("docs://readme")
def readme() -> str:
    """项目说明"""
    return "这是项目说明"

@server.prompt()
def review(code: str) -> str:
    """审查一段代码"""
    return f"请审查这段代码：\n{code}"

async def main():
    async with Client(server) as client:
        resource = await client.read_resource("docs://readme")
        print(resource.contents[0].text)  # => 这是项目说明

        prompt = await client.get_prompt("review", {"code": "x = 1"})
        print(prompt.messages[0].role)  # => user

asyncio.run(main())
```

## 传输方式 {#transport}

Server 和 Client 之间有两种主要的传输方式：

| 对比项 | stdio | Streamable HTTP |
| --- | --- | --- |
| 运行位置 | 本地子进程 | 远程服务 |
| 通信 | 标准输入和输出 | HTTP 请求 |
| 适合 | 读写本地文件、命令行工具 | 多用户共享的服务 |
| 鉴权 | 不需要，继承本地权限 | OAuth 等方式 |
| 启动 | `server.run()` | `server.run(transport="streamable-http")` |

stdio 模式下 Host 启动子进程并通过管道通信。

```python
§ import pathlib
§ pathlib.Path("weather_server.py").write_text('''
§ from mcp.server.mcpserver import MCPServer
§ server = MCPServer("weather")
§ @server.tool()
§ def get_weather(city: str) -> str:
§     """查询天气"""
§     return f"{city}：晴"
§ server.run()
§ ''', "utf-8")
import asyncio
import sys

from mcp import Client, StdioServerParameters

async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=["weather_server.py"],
    )
    async with Client(params) as client:
        result = await client.call_tool("get_weather", {"city": "上海"})
        print(result.content[0].text)  # => 上海：晴

asyncio.run(main())
```

:::warn stdio 模式不要 print
stdio 模式下，标准输出是协议通道。代码里一个 `print` 就会破坏通信，日志要写到标准错误。
:::

连接远程服务时，把网址传给 `Client` 就行。

## 接入 Agent 循环 {#agent}

把 MCP 接进「工具调用循环」一章的 Agent 只要两步：把 `list_tools` 的结果转成模型要的工具定义，模型要调用时转给 `call_tool`。

```python
§ import fakellm
§ fakellm.serve(fakellm.tool("get_weather", city="北京"), "北京今天晴")
§ MODEL = "demo"
§ from mcp.server.mcpserver import MCPServer
§ server = MCPServer("weather")
§ @server.tool()
§ def get_weather(city: str) -> str:
§     """查询城市当前的天气"""
§     return f"{city}：晴"
import asyncio
import json

from mcp import Client
from openai import AsyncOpenAI

llm = AsyncOpenAI()

def to_openai(tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }

async def run_agent(mcp: Client, task: str) -> str:
    tools = [to_openai(t) for t in (await mcp.list_tools()).tools]
    messages = [{"role": "user", "content": task}]
    for _ in range(10):
        response = await llm.chat.completions.create(
            model=MODEL, messages=messages, tools=tools,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            return message.content
        for call in message.tool_calls:
            result = await mcp.call_tool(
                call.function.name,
                json.loads(call.function.arguments),
            )
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result.content[0].text,
            })
    raise RuntimeError("超过最大步数")

async def main():
    async with Client(server) as mcp:
        print(await run_agent(mcp, "北京天气？"))  # => 北京今天晴

asyncio.run(main())
```

现成的 Agent 应用大多通过配置文件接入 Server，不用写代码。下面是常见的写法，具体文件位置看各应用的文档。

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["weather_server.py"]
    }
  }
}
```

## 安全 {#security}

MCP Server 能执行任意代码，接入之前要像审查依赖一样审查它：

- **只用可信来源的 Server。** 它运行时拥有你的本地权限。
- **工具描述也不可信。** 描述会进入模型的上下文，恶意 Server 可以在里面藏指令，规范明确要求把这些描述当作不可信内容。
- **工具调用要经过确认。** 规范要求 Host 在调用工具前取得用户同意。
- **限制权限。** 给 Server 的 Token 只开必要的权限，只读就够的时候不要给写权限。
- **注意工具结果。** Server 返回的内容可能包含恶意指令，详见「Prompt Injection」。

:::map MCP 写法对照
| python | java | kotlin | note |
| --- | --- | --- | --- |
| `MCPServer("name")` | `McpServer.sync(transport)` | `McpServer.sync(transport)` | 创建服务 |
| `@server.tool()` | `.toolCall(tool, handler)` | `.toolCall(tool) { }` | 注册工具 |
| `server.run()` | `StdioServerTransportProvider` | `StdioServerTransportProvider` | 默认用 stdio |
| `Client(server)` | `McpClient.sync(transport)` | `McpClient.sync(transport)` | 连接服务 |
| `client.call_tool()` | `client.callTool()` | `client.callTool()` | 调用工具 |
:::

:::recap
- MCP 统一了 Agent 应用和外部工具的连接方式，工具写一次到处能用
- Host 是应用，Client 是连接器，Server 提供 Tools、Resources 和 Prompts
- Python SDK 2.x 用 `MCPServer`，函数加 `@server.tool()` 就是工具
- 本地用 stdio，远程用 Streamable HTTP，stdio 模式下不能向标准输出打印
- 接入 Agent 时，把 `list_tools` 转成工具定义，把调用转给 `call_tool`
- Server 拥有真实权限，工具描述和返回内容都不可信
:::
