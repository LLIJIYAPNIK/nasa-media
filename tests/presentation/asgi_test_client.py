from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ASGIResponse:
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")


async def asgi_get(app: Any, path: str) -> ASGIResponse:
    """Минимальный ASGI-клиент для GET-запросов без тела.

    fastapi.testclient.TestClient не используется: googletrans==4.0.0rc1
    жёстко пинит httpx==0.13.3 (без httpx.BaseTransport), несовместимый с
    современным starlette.testclient — а трогать перевод вне скоупа этой
    фичи (см. docs/tz/TZ-web.md). Для простых GET-запросов без вебсокетов/
    стриминга голого ASGI-протокола достаточно.
    """

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 123),
        "scheme": "http",
    }

    pending_messages: list[dict[str, Any]] = [{"type": "http.request", "body": b"", "more_body": False}]

    async def receive() -> dict[str, Any]:
        return pending_messages.pop(0) if pending_messages else {"type": "http.disconnect"}

    response_status: dict[str, int] = {}
    response_headers: dict[str, str] = {}
    body_chunks: list[bytes] = []

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            response_status["status"] = message["status"]
            response_headers.update({key.decode(): value.decode() for key, value in message.get("headers", [])})
        elif message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))

    await app(scope, receive, send)

    return ASGIResponse(status_code=response_status["status"], headers=response_headers, body=b"".join(body_chunks))
