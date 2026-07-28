from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Переменная окружения {name} не задана — см. .env.example")
    return value


BOT_TOKEN: str = _require("BOT_TOKEN")
NASA_API_KEY: str = _require("NASA_API_KEY")
DB_URL: str = _require("DB_URL")
ADMIN_CHAT_ID: int = int(_require("ADMIN_CHAT_ID"))
APOD_LOWER_BOUND: date = date.fromisoformat(_require("APOD_LOWER_BOUND"))
NASA_APOD_URL: str = _require("NASA_APOD_URL")
NASA_EPIC_URL: str = _require("NASA_EPIC_URL")
NASA_DONKI_URL: str = _require("NASA_DONKI_URL")
NASA_NEOWS_URL: str = _require("NASA_NEOWS_URL")
NASA_EONET_URL: str = _require("NASA_EONET_URL")
