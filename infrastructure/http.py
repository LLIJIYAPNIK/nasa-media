from __future__ import annotations

import aiohttp


async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict | None = None):
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        # content_type=None: некоторые NASA-эндпоинты (например EONET) иногда
        # отдают валидный JSON с неверным заголовком Content-Type
        # (application/rss+xml) — без этого aiohttp кидает ContentTypeError
        # на корректном теле ответа.
        return await response.json(content_type=None)


async def fetch_bytes(
    session: aiohttp.ClientSession, url: str, params: dict | None = None, headers: dict | None = None
) -> bytes:
    async with session.get(url, params=params, headers=headers) as response:
        response.raise_for_status()
        return await response.read()
