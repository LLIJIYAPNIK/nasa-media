from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse, Response

from application.web.homepage_detail_query import GetHomepageDetail, UnknownHomepageDetailKind
from application.web.homepage_query import GetHomepageSnapshot, HomepageSnapshot
from infrastructure.web.event_map_cache import EventMapFileCache
from infrastructure.web.snapshot_cache import SnapshotCache

# Порядок и подписи — вариант 4b дизайна (боковая иконочная навигация),
# см. docs/tz/TZ-web.md.
NAV_ITEMS = (
    {"path": "/", "label": "Главная"},
    {"path": "/apod", "label": "APOD"},
    {"path": "/epic", "label": "EPIC"},
    {"path": "/asteroids", "label": "Астер."},
    {"path": "/space-weather", "label": "Погода"},
    {"path": "/earth-events", "label": "События"},
    {"path": "/weekly-highlights", "label": "Итоги"},
)

# Разделы без вёрстки в этом заходе — заглушка-роут вместо 404/href="#",
# чтобы навигация 4b была рабочей уже сейчас (см. TZ-web.md, «Роуты»).
# "/epic" здесь больше нет — своя реализация в epic_router.py (см.
# docs/tz/TZ-web-epic.md); при отсутствии данных NASA сама страница
# рендерит тот же placeholder.html, так что заглушка не пропадает.
PLACEHOLDER_SECTIONS = {
    "/apod": "APOD",
    "/epic": "EPIC",
    "/asteroids": "Астероиды",
    "/space-weather": "Космическая погода",
    "/earth-events": "События Земли",
    "/weekly-highlights": "Итоги недели",
}


async def _get_or_compute_snapshot(
    cache: SnapshotCache, get_snapshot: GetHomepageSnapshot, today: date
) -> HomepageSnapshot:
    snapshot = cache.get(today)
    if snapshot is None:
        snapshot = await get_snapshot.execute(today)
        cache.set(today, snapshot)
    return snapshot


def build_homepage_router(
    templates: Jinja2Templates,
    get_snapshot: GetHomepageSnapshot,
    get_detail: GetHomepageDetail,
    cache: SnapshotCache,
    event_map_cache: EventMapFileCache,
) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    async def homepage(request: Request) -> HTMLResponse:
        snapshot = await _get_or_compute_snapshot(cache, get_snapshot, date.today())
        return templates.TemplateResponse(request, "homepage.html", {"snapshot": snapshot})

    @router.get("/api/homepage/snapshot")
    async def homepage_snapshot() -> dict:
        snapshot = await _get_or_compute_snapshot(cache, get_snapshot, date.today())
        return asdict(snapshot)

    @router.get("/api/homepage/details/{kind}")
    async def homepage_detail(kind: str) -> dict:
        try:
            detail = await get_detail.execute(kind, date.today())
        except UnknownHomepageDetailKind as exc:
            raise HTTPException(status_code=404, detail=f"Неизвестный тип карточки: {exc}") from exc
        return asdict(detail)

    @router.get("/api/homepage/earth-event-map/{cache_key}.png")
    async def earth_event_map(cache_key: str) -> Response:
        # cache_key валидируется внутри EventMapFileCache (см.
        # infrastructure/web/event_map_cache.py) — небезопасные значения
        # (path traversal и т.п.) тихо превращаются в None -> 404, файл на
        # диске никогда не открывается по непроверенному пути.
        image_bytes = await event_map_cache.get(cache_key)
        if image_bytes is None:
            raise HTTPException(status_code=404, detail="Карта не найдена")
        return Response(content=image_bytes, media_type="image/png")

    def _make_placeholder_endpoint(section_title: str):
        async def _placeholder(request: Request) -> HTMLResponse:
            return templates.TemplateResponse(request, "placeholder.html", {"section_title": section_title})

        return _placeholder

    for path, section_title in PLACEHOLDER_SECTIONS.items():
        router.add_api_route(path, _make_placeholder_endpoint(section_title), methods=["GET"])

    return router
