from __future__ import annotations

from dataclasses import asdict
from datetime import date
from datetime import date as date_

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from application.web.apod_gallery_query import GetApodGalleryPage

# Тайлов на страницу — константа для SSR первой страницы и клиентских
# догрузок; шаблон прокидывает её в data-limit, apod_gallery.js читает
# оттуда, а не хранит своё число (docs/tz/TZ-web-apod.md, «Пагинация»).
APOD_GALLERY_PAGE_SIZE = 30


def build_apod_router(templates: Jinja2Templates, get_gallery_page: GetApodGalleryPage) -> APIRouter:
    router = APIRouter()

    @router.get("/apod")
    async def apod_gallery(request: Request) -> HTMLResponse:
        page = await get_gallery_page.execute(before=None, today=date.today())
        return templates.TemplateResponse(
            request,
            "apod.html",
            {"page": page, "page_size": APOD_GALLERY_PAGE_SIZE},
        )

    @router.get("/api/apod/entries")
    async def apod_entries(before: date_ | None = None, limit: int | None = None) -> dict:
        page = await get_gallery_page.execute(before=before, today=date.today(), page_size=limit)
        return asdict(page)

    return router
