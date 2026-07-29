from __future__ import annotations

from typing import Any
from urllib.parse import urlencode


class FakeResponse:
    def __init__(self, *, json_data: Any = None, body: bytes = b"", status: int = 200) -> None:
        self._json_data = json_data
        self._body = body
        self.status = status
        self.json_content_type_args: list[str | None] = []

    async def json(self, content_type: str | None = "application/json") -> Any:
        self.json_content_type_args.append(content_type)
        return self._json_data

    async def read(self) -> bytes:
        return self._body

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def build_url(base_url: str, params: dict | None) -> str:
    if not params:
        return base_url
    return f"{base_url}?{urlencode(params)}"


class FakeClientSession:
    """Подменяет aiohttp.ClientSession в тестах NASA-клиентов — без сети и
    без завязки на aioresponses (несовместим с текущей версией aiohttp,
    см. TZ-core-transfer.md, «Решения»)."""

    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self._responses = responses
        self.requested_urls: list[str] = []

    def get(self, url: str, params: dict | None = None, **kwargs: Any) -> FakeResponse:
        full_url = build_url(url, params)
        self.requested_urls.append(full_url)
        try:
            return self._responses[full_url]
        except KeyError:
            raise AssertionError(f"Незапланированный запрос: {full_url}") from None

    async def __aenter__(self) -> FakeClientSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class AnyUrlClientSession:
    """Как FakeClientSession, но отдаёт один и тот же фейковый ответ на
    любой GET — для клиентов, которые бьют по неизвестному заранее набору
    URL (тайлы карт: z/x/y перебираются кодом, не тестом)."""

    def __init__(self, response_body: bytes) -> None:
        self._response_body = response_body
        self.requested_urls: list[str] = []
        self.last_headers: dict | None = None

    def get(self, url: str, params: dict | None = None, **kwargs: Any) -> FakeResponse:
        self.requested_urls.append(build_url(url, params))
        self.last_headers = kwargs.get("headers")
        return FakeResponse(body=self._response_body)

    async def __aenter__(self) -> AnyUrlClientSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FailingClientSession:
    """Симулирует сетевую ошибку (не HTTP-статус — реальный
    aiohttp.ClientError, в отличие от FakeResponse.raise_for_status(),
    который для простоты тестов бросает RuntimeError)."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.requested_urls: list[str] = []

    def get(self, url: str, params: dict | None = None, **kwargs: Any) -> FakeResponse:
        self.requested_urls.append(build_url(url, params))
        raise self._exc

    async def __aenter__(self) -> FailingClientSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False
