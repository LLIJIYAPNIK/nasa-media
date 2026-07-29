from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse, Response

from application.web.epic_page_query import EpicPageSnapshot, GetEpicPageSnapshot
from infrastructure.web.epic_snapshot_cache import EpicPageSnapshotCache
from infrastructure.web.epic_texture_cache import EpicTextureFileCache


async def _get_or_compute_epic_snapshot(
    cache: EpicPageSnapshotCache, get_snapshot: GetEpicPageSnapshot
) -> EpicPageSnapshot | None:
    snapshot = cache.get()
    if snapshot is None:
        snapshot = await get_snapshot.execute()
        if snapshot is not None:
            cache.set(snapshot)
    return snapshot


def build_epic_router(
    templates: Jinja2Templates,
    get_snapshot: GetEpicPageSnapshot,
    cache: EpicPageSnapshotCache,
    texture_cache: EpicTextureFileCache,
) -> APIRouter:
    router = APIRouter()

    @router.get("/epic")
    async def epic_page(request: Request) -> HTMLResponse:
        snapshot = await _get_or_compute_epic_snapshot(cache, get_snapshot)
        if snapshot is None:
            # NASA не отдала ни одной известной даты EPIC (или у последней
            # — 0 кадров) — переиспользуем существующую заглушку вместо
            # отдельной страницы ошибки, см. docs/tz/TZ-web-epic.md.
            return templates.TemplateResponse(request, "placeholder.html", {"section_title": "EPIC"})
        return templates.TemplateResponse(request, "epic.html", {"snapshot": snapshot})

    @router.get("/api/epic/textures/{cache_key}.jpg")
    async def epic_texture(cache_key: str) -> Response:
        image_bytes = await texture_cache.get(cache_key)
        if image_bytes is None:
            raise HTTPException(status_code=404, detail="Текстура не найдена")
        return Response(content=image_bytes, media_type="image/jpeg")

    return router
