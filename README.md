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

Сейчас в репозитории — только бутстрап (структура проекта, зависимости).
Перенос ядра бота (APOD + EPIC) в DDD-слои ведётся по
[TZ-ddd-refactor.md](./TZ-ddd-refactor.md) отдельной веткой/PR. До его
завершения `main.py` для запуска бота ещё не существует.

Целевая раскладка:

```
domain/               — чистые правила, без I/O
application/          — use-case'ы
infrastructure/        — БД, NASA API, Telegram, файлы, перевод
presentation/telegram/ — aiogram-роутеры
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

```
uv run python main.py
```

(появится после переноса ядра бота, см. «Статус» выше)

## Лицензия

[MIT](./LICENSE). Лицензия покрывает только код бота — данные NASA остаются
public domain по политике NASA независимо от лицензии репозитория.
