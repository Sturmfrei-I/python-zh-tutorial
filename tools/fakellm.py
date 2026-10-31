"""校验示例用的假大模型：在本机起一个 OpenAI 兼容服务，按脚本返回回答。

示例里用隐藏行启动它，读者看到的代码不用改，也不需要 API Key：

    § import fakellm
    § fakellm.serve("你好", fakellm.tool("get_weather", city="北京"), "晴")

serve 的每个参数对应一次 /chat/completions 请求：
    - 字符串：普通文本回答
    - tool(...)：一次工具调用，tools(...) 同时调用多个
    - error(429)：返回错误状态码
    - dict：原样作为 assistant 消息

embed 按文本返回事先写好的向量，没写的文本用字符哈希算一个。
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

requests: list[dict] = []
USAGE = {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17}


def tool(name: str, **arguments) -> dict:
    return tools((name, arguments))


def tools(*calls: tuple[str, dict]) -> dict:
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": f"call_{i}", "type": "function",
         "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}
        for i, (name, args) in enumerate(calls)]}


def error(status: int, message: str = "fake error") -> dict:
    return {"status": status, "message": message}


def vector_of(text: str, dimensions: int = 8) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    return [digest[i] / 255 - 0.5 for i in range(dimensions)]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    script: list = []
    vectors: dict[str, list[float]] = {}
    lock = threading.Lock()

    def log_message(self, *args):
        pass

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        requests.append(body)
        if self.path.endswith("/embeddings"):
            texts = [body["input"]] if isinstance(body["input"], str) else body["input"]
            data = [{"object": "embedding", "index": i,
                     "embedding": self.vectors.get(t) or vector_of(t, body.get("dimensions", 8))}
                    for i, t in enumerate(texts)]
            self.send_json(200, {"object": "list", "data": data, "model": body["model"],
                                 "usage": {"prompt_tokens": 4, "total_tokens": 4}})
            return

        with self.lock:
            reply = self.script.pop(0) if self.script else "（脚本已用完）"
        if isinstance(reply, dict) and "status" in reply:
            self.send_json(reply["status"], {"error": {"message": reply["message"], "type": "fake"}})
            return
        message = reply if isinstance(reply, dict) else {"role": "assistant", "content": reply}
        finish = "tool_calls" if message.get("tool_calls") else "stop"
        if body.get("stream"):
            self.stream(body, message, finish)
        else:
            self.send_json(200, {"id": "chatcmpl-fake", "object": "chat.completion", "created": 0,
                                 "model": body["model"], "usage": USAGE,
                                 "choices": [{"index": 0, "message": message, "finish_reason": finish}]})

    def stream(self, body: dict, message: dict, finish: str) -> None:
        def chunk(delta: dict, reason=None, usage=None) -> bytes:
            choices = [{"index": 0, "delta": delta, "finish_reason": reason}] if usage is None else []
            event = {"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 0,
                     "model": body["model"], "choices": choices, "usage": usage}
            return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(chunk({"role": "assistant", "content": ""}))
        for piece in message.get("content") or "":
            self.wfile.write(chunk({"content": piece}))
        for i, call in enumerate(message.get("tool_calls") or []):
            self.wfile.write(chunk({"tool_calls": [{**call, "index": i}]}))
        self.wfile.write(chunk({}, finish))
        if body.get("stream_options", {}).get("include_usage"):
            self.wfile.write(chunk({}, usage=USAGE))
        self.wfile.write(b"data: [DONE]\n\n")
        self.close_connection = True


def serve(*replies, embed: dict[str, list[float]] | None = None) -> None:
    Handler.script = list(replies)
    Handler.vectors = embed or {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    os.environ["OPENAI_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/v1"
    os.environ["OPENAI_API_KEY"] = "test"
