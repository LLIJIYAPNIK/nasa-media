# nasa-media

Telegram-бот на [aiogram 3](https://docs.aiogram.dev/), отдающий контент NASA:
APOD (Astronomy Picture of the Day) и EPIC (снимки Земли). Хранилище —
PostgreSQL через SQLAlchemy 2.0 async.

Это переезд и переработка дипломного проекта Skillbox
[NasaAPI-bot-skillbox-diploma](https://github.com/LLIJIYAPNIK/NasaAPI-bot-skillbox-diploma)
в новый репозиторий с DDD/Clean Architecture и без привязки к бренду курса.
Старый репозиторий остаётся публичным как ссылка на первую версию проекта и
будет переведён в архив, когда основной функционал переедет сюда.

## Статус

Ядро (APOD + EPIC: кеш через admin-чат, рассылка по подписке, FSM-сценарии
выбора даты, атрибуция copyright для APOD) перенесено в DDD-слои. Дальше по
плану — GIF/таймлапс для EPIC и день рождения для APOD, см.
[docs/tz/](./docs/tz/).

Раскладка:

```
domain/               — чистые правила, без I/O
application/          — use-case'ы
infrastructure/        — БД, NASA API, Telegram, файлы, перевод
presentation/telegram/ — aiogram-роутеры
presentation/web/      — FastAPI-приложение (главная страница, см. docs/tz/TZ-web.md)
```

## Установка

Зависимости управляются через [uv](https://docs.astral.sh/uv/):

```
uv sync
```

## Конфигурация

Скопируйте `.env.example` в `.env` и заполните реальными значениями
(`BOT_TOKEN`, `NASA_API_KEY`, `DB_URL`, `ADMIN_CHAT_ID`). `.env` — в
`.gitignore`, реальные секреты в git не попадают.

## Запуск

Бот:

```
uv run python main.py
```

Веб-интерфейс (отдельный ASGI-процесс, тот же `.env`, см. docs/tz/TZ-web.md):

```
uv run uvicorn presentation.web.app:app --reload
```

## Проверки

```
uv run pytest              # тесты
uv run mypy .               # типы
uv run ruff check .         # линт
uv run ruff format --check .  # форматирование
```

Тот же набор прогоняется в CI (`.github/workflows/ci.yml`) на каждый push в
`main` и на каждый PR.

## Лицензия

[MIT](./LICENSE). Лицензия покрывает только код бота — данные NASA остаются
public domain по политике NASA независимо от лицензии репозитория.
