"""教学用 JSON-RPC 2.0 子集：一行一个请求/响应，执行仍委托给 RunService。

这不是 EvoFlow App Server 的完整协议实现；目前只覆盖 initialize、ping、turn/start。
流式事件、并发 run、interrupt、bridge/embed 和宿主鉴权留给后续功能单元。
"""

import json
import sys
from typing import TextIO
from uuid import uuid4


def _response(request_id: object, result: object = None, error: dict | None = None) -> dict:
    """统一 JSON-RPC 响应封装，避免每个方法拼出不同格式。"""
    message = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        message["error"] = error
    else:
        message["result"] = result
    return message


def serve_stdio(service, sessions, owner_id: str = "local-user", stdin: TextIO | None = None,
                stdout: TextIO | None = None) -> None:
    """逐行处理请求；stdio 只负责协议，核心业务仍走同一个 RunService。"""
    source = stdin or sys.stdin
    sink = stdout or sys.stdout

    for line in source:
        request = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("请求必须是 JSON 对象")
            if request.get("jsonrpc") != "2.0":
                raise ValueError("jsonrpc 必须是 2.0")
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})
            if not isinstance(method, str) or not isinstance(params, dict):
                raise ValueError("method 必须是字符串，params 必须是对象")

            if method == "initialize":
                result = {"serverInfo": {"name": "WorkAgentHarness", "version": "0.1.0"},
                          "capabilities": {"turnStart": True}}
            elif method == "server/ping":
                result = {"ok": True}
            elif method == "turn/start":
                text = params.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("params.text 必须是非空字符串")
                session_id = params.get("sessionId") or uuid4().hex
                if not isinstance(session_id, str):
                    raise ValueError("params.sessionId 必须是字符串")
                sessions.create(session_id, owner_id)
                run = service.execute(owner_id, session_id, text)
                result = {"sessionId": session_id, "runId": run.run_id,
                          "status": run.status, "answer": run.answer,
                          "errorCode": run.error_code}
            else:
                if "id" in request:
                    sink.write(json.dumps(_response(request_id, error={
                        "code": -32601, "message": f"未知方法: {method}"
                    }), ensure_ascii=False) + "\n")
                    sink.flush()
                continue

            # JSON-RPC notification 没有 id，按协议不返回响应。
            if "id" in request:
                sink.write(json.dumps(_response(request_id, result=result), ensure_ascii=False) + "\n")
                sink.flush()
        except json.JSONDecodeError:
            sink.write(json.dumps(_response(None, error={
                "code": -32700, "message": "无效 JSON"
            }), ensure_ascii=False) + "\n")
            sink.flush()
        except ValueError as exc:
            if not isinstance(request, dict) or "id" in request:
                sink.write(json.dumps(_response(request.get("id") if isinstance(request, dict) else None,
                                                error={"code": -32602, "message": str(exc)}),
                                      ensure_ascii=False) + "\n")
                sink.flush()
        except Exception:  # noqa: BLE001 - 协议边界不能把内部异常或密钥回显给宿主
            if not isinstance(request, dict) or "id" in request:
                sink.write(json.dumps(_response(request.get("id") if isinstance(request, dict) else None,
                                                error={"code": -32603, "message": "内部错误"}),
                                      ensure_ascii=False) + "\n")
                sink.flush()

