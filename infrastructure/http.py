from __future__ import annotations

import aiohttp


async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict | None = None):
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        return await response.json()


async def fetch_bytes(session: aiohttp.ClientSession, url: str, params: dict | None = None) -> bytes:
    async with session.get(url, params=params) as response:
        response.raise_for_status()
        return await response.read()
