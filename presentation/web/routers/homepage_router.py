from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

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
PLACEHOLDER_SECTIONS = {
    "/apod": "APOD",
    "/epic": "EPIC",
    "/asteroids": "Астероиды",
    "/space-weather": "Космическая погода",
    "/earth-events": "События Земли",
    "/weekly-highlights": "Итоги недели",
}


def build_homepage_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()

    def _make_placeholder_endpoint(section_title: str):
        async def _placeholder(request: Request) -> HTMLResponse:
            return templates.TemplateResponse(request, "placeholder.html", {"section_title": section_title})

        return _placeholder

    for path, section_title in PLACEHOLDER_SECTIONS.items():
        router.add_api_route(path, _make_placeholder_endpoint(section_title), methods=["GET"])

    return router
