# TZ-core-transfer.md — перенос ядра (APOD + EPIC) в DDD-слои

## Цель

Перенести логику APOD/EPIC из `NasaAPI-bot-skillbox-diploma` в скелет
`domain/application/infrastructure/presentation/telegram`, созданный бутстрапом
(PR #1), по контракту из `TZ-ddd-refactor.md`. Заодно закрыть известные баги
из CLAUDE.md (пункт 2), не связанные с переводом. Код переносится осмысленно
(логика и решения), файлы старого репозитория не копируются как есть.

## Уточнения к TZ-ddd-refactor.md

При детальном проектировании нашлись два расхождения с уже утверждённым
TZ-ddd-refactor.md — фиксирую здесь как исправление, а не молча переигрываю:

- **`ApodEntry.copyright` убирается из персистентной сущности.** В
  TZ-ddd-refactor.md это поле было зарезервировано на сущности «про запас».
  Но CLAUDE.md (пункт 4, «Авторские права») прямо говорит: «Поле не
  обязательно хранить в БД отдельно — кеш и так работает через `message_id`,
  достаточно учитывать `copyright` на этапе формирования подписи перед первой
  отправкой в admin-чат». Значит `ApodEntry` (персистентная запись кеша)
  остаётся `date` + `message_id`, без `copyright`. `copyright` будет жить
  только в `MediaPayload` (транзиентный DTO при первой публикации) — этим
  займётся TZ-copyright.md, здесь только оставляю для него ровно одну точку
  входа: сборка подписи внутри `ApodProvider.fetch()`.
- **Поле под день рождения в `User` не резервируется сейчас.** CLAUDE.md
  (пункт 3) сам описывает добавление колонки как часть задачи «День рождения
  для APOD» — значит миграция схемы `Users` тоже принадлежит TZ-birthday.md,
  не этому шагу. `User` в этом TZ — `chat_id`, `apod_subscribed`,
  `epic_subscribed`, без дополнительных полей.

## Что переносится (карта старый код → новый слой)

| Старое | Новое |
|---|---|
| `database/models.py` (`APOD`, `EPIC`, `Users`) | `infrastructure/db/models.py` (+ новая `EpicFrameModel`, см. «Решения») |
| `database/crud.py` (`DatabaseManager`) | `infrastructure/db/repositories.py` — конкретные репозитории на каждую модель вместо одного универсального класса под три таблицы |
| `handlers/APOD/tools/await_date_data.py` (`current_date`, отправка в admin-чат, сохранение в БД, пересылка пользователю) | `infrastructure/nasa/apod_client.py` (`ApodProvider.fetch`) + `infrastructure/telegram/admin_chat_gateway.py` + `application/media/deliver_media.py` |
| `handlers/EPIC/tools/await_message.py` + `send_photo.py` | `infrastructure/nasa/epic_client.py` (`EpicProvider.fetch`) + `infrastructure/telegram/admin_chat_gateway.py` (общий с APOD) |
| `handlers/APOD/tools/sender.py`, `handlers/EPIC/tools/sender.py` (`subscribe_*_send_message`) | `application/media/broadcast.py` (`BroadcastSubscribedUsers`, один класс на оба источника) |
| `handlers/APOD/subscribe.py`, `handlers/EPIC/subscribe.py` | `application/subscriptions/manage_subscription.py` (`SetSubscription`, один use-case) |
| `handlers/EPIC/fill_db.py` (`update_dates`, `dates.txt`) | `application/epic/refresh_availability.py` (`RefreshEpicAvailability`) — источник правды теперь только БД, без `dates.txt` (см. «Решения») |
| `handlers/APOD/tools/is_correct_date.py` | не переносится как есть — заменяется на `datetime.date.fromisoformat`/`strptime` (см. «Решения») |
| `handlers/APOD/tools/create_date_list.py` | `domain/media/value_objects.py` (`DateRange.iter_dates()`) |
| `handlers/start_handler.py` | `application/users/register_user.py` (`GetOrCreateUser`) + `presentation/telegram/routers/start_router.py` |
| `main.py` + `aiogram_run.py` | новый `main.py` — composition root (сборка зависимостей, polling, периодический цикл) |
| `keyboards/inline/*` | `presentation/telegram/keyboards/*` — переносится почти без изменений, это уже тонкий UI-слой |

## Целевые файлы

```
domain/
  media/entities.py          — ApodEntry(date, message_id); EpicDay(date, frames); EpicFrame(telegram_file_id, position)
  media/value_objects.py     — MediaSourceKind; DateRange(start, end) с валидацией и .iter_dates(); EPIC_LOWER_BOUND = date(2015, 6, 13) (см. «Решения»)
  media/exceptions.py        — MediaNotAvailable
  users/entities.py          — User(chat_id, apod_subscribed, epic_subscribed) + is_subscribed()/with_subscription()

application/
  media/ports.py             — MediaProvider, AdminChatGateway, ApodRepository, EpicRepository, UserRepository (Protocol), MediaPayload (DTO)
  media/deliver_media.py     — DeliverMediaForDate
  media/broadcast.py         — BroadcastSubscribedUsers
  subscriptions/manage_subscription.py — SetSubscription
  users/register_user.py     — GetOrCreateUser
  epic/refresh_availability.py — RefreshEpicAvailability + порт EpicAvailabilityIndex

infrastructure/
  db/models.py                — ApodModel, EpicDayModel, EpicFrameModel(FK), UserModel
  db/session.py                — async engine/session (DB_URL из конфига), create_all при старте (см. «Решения»)
  db/repositories.py           — реализации *Repository на SQLAlchemy
  nasa/apod_client.py          — ApodProvider (aiohttp, перевод, сборка подписи)
  nasa/epic_client.py          — EpicProvider (aiohttp, N кадров за дату)
  nasa/epic_availability_client.py — реализация EpicAvailabilityIndex (список дат с NASA)
  telegram/admin_chat_gateway.py — AdminChatGateway (публикация в admin-чат + пересылка пользователю, общая для обоих источников)
  translation/ru_translator.py — обёртка над googletrans, поведение не меняется
  files/temp_file.py           — временный файл с uuid4-суффиксом, контекстный менеджер с гарантированным удалением

presentation/telegram/
  routers/start_router.py, apod_router.py, epic_router.py — тонкие, вызывают application-сервисы
  states.py                    — ApodCurrentDateForm, ApodDateRangeForm, EpicDateForm (переименовано из двух одинаковых `Form` в разных модулях старого кода — во избежание путаницы одноимённых классов)
  keyboards/                   — перенос keyboards/inline/* почти без изменений

main.py — composition root: движок БД, репозитории, providers, gateway, translator,
use-case'ы, aiogram Bot/Dispatcher, роутеры, периодический цикл рассылки.
```

## Решения по неоднозначностям

- **`AsyncIOScheduler` убирается, не чинится.** CLAUDE.md формулирует это как
  открытый выбор («либо использовать по назначению, либо убрать»). Реальная
  потребность — один периодический цикл раз в сутки (обновление дат EPIC +
  две рассылки). Уже работающий `asyncio.create_task` с `asyncio.sleep(interval)`
  полностью закрывает эту потребность; вводить APScheduler как зависимость и
  конфигурацию ради одной задачи — это усложнение без функционального
  выигрыша (см. принцип «не проектировать под гипотетическое будущее» в
  CLAUDE.md). Оставляю периодический цикл на `asyncio`, но без бага «создан,
  не запущен» — теперь он и создаётся, и стартует в `main.py`. **Если у тебя
  другие планы на APScheduler (например, разные интервалы для разных задач в
  будущем) — скажи сейчас, до того как я его выброшу.**
- **`current_date()` → `ApodProvider.fetch()` на `aiohttp`.** Закрывает баг
  блокирующего `requests.get` внутри async-функции; `aiohttp.ClientSession`
  и так уже есть рядом (для скачивания картинок).
- **Временный файл — `infrastructure/files/temp_file.py` с `uuid4()` в имени,
  через контекстный менеджер.** Закрывает и гонку при параллельных запросах
  (баг из CLAUDE.md), и попутно — ненадёжное удаление файла в старом коде
  (удаление в конце функции не гарантировано при ранних `return`/исключениях);
  `try/finally` через контекстный менеджер решает оба сразу, это один и тот же
  участок кода.
- **`except Exception` вокруг `bot.send_photo` сужается до
  `aiogram.exceptions.TelegramBadRequest`.** Это и есть конкретная ошибка,
  которую ловит текущий код (Telegram не смог сам скачать изображение по
  прямой ссылке) — раньше маскировались вообще любые ошибки, включая полные
  сетевые сбои или неверные учётные данные бота.
- **`fill_db.dates.txt` не переносится — `RefreshEpicAvailability` сверяется
  с БД напрямую, а не с отдельным плоским файлом.** Даты, известные NASA,
  и так по факту оказываются в `EpicDay` (изначально с пустым списком кадров,
  как только обнаружены, до первого реального запроса кадров пользователем).
  Диффать список от NASA нужно против уже сохранённых `EpicDay.date`, а не
  против `dates.txt` — иначе два источника правды об одном и том же факте
  (прямое нарушение принципа CLAUDE.md «один источник правды на факт»),
  и `DATES_FILE_PATH` из конфига можно убрать целиком.
- **`is_correct_date.py` не переносится — валидация через
  `datetime.date.fromisoformat` / `strptime`.** Старая реализация вручную
  таблицей дней в месяце и особым случаем високосного года дублирует то, что
  уже делает `datetime.strptime` (кидает `ValueError` на `2024-02-30` и
  корректно понимает високосные годы через встроенный календарь). Отдельная
  ручная таблица дней — лишний код с шансом разойтись со стдлибом.
- **Границы дат: `APOD_LOWER_BOUND` остаётся в `.env` (уже есть в
  `.env.example`), нижняя граница EPIC (`2015-06-13`) становится доменной
  константой, а не новой переменной окружения.** В старом коде она была
  жёстко зашита в хендлере, а не вынесена в конфиг — эта TZ не меняет, что
  именно конфигурируемо, только переносит константу в `domain` вместо
  `handlers/EPIC/start_finish.py`.
- **Миграции схемы — по-прежнему `Base.metadata.create_all` при старте,
  Alembic не вводится.** Старый код обходился без миграций; вводить Alembic
  сейчас — это тулинг, не запрошенный ни в CLAUDE.md, ни в текущих 5 пунктах.
  Возвращаемся к вопросу, когда/если схема начнёт часто меняться в проде.
- **`EpicFrame` — таблица с FK на `EpicDay`, не строка `file_id` через
  пробел** (уже зафиксировано в TZ-ddd-refactor.md, здесь просто подтверждаю
  конкретные колонки: `id`, `epic_day_id`, `telegram_file_id`, `position`).
- **Новые dev-зависимости для тестов инфраструктурного слоя:**
  `aiosqlite` (репозитории — против SQLite in-memory вместо реального
  Postgres) и `aioresponses` (моки ответов NASA API поверх `aiohttp`).
  Добавляются через `uv add --dev` в момент написания соответствующих тестов.

## Тестирование (по слоям, как в TZ-ddd-refactor.md)

- `domain` — `DateRange` (границы, `iter_dates`), `User.with_subscription`.
- `application` — `DeliverMediaForDate`/`BroadcastSubscribedUsers`/
  `SetSubscription`/`RefreshEpicAvailability` с фейковыми портами (без
  реальной БД/сети/Telegram).
- `infrastructure` — репозитории против SQLite in-memory; NASA-клиенты с
  `aioresponses`; `admin_chat_gateway` с `AsyncMock` вместо `aiogram.Bot`.
- `presentation` — точечные тесты роутинга (нужный use-case вызван с нужными
  параметрами по callback_data/состоянию FSM).

## Что реализовано этой TZ

Полный перенос APOD+EPIC (кеш через admin-чат, рассылка по подписке, FSM-сценарии
выбора даты) на структуру из TZ-ddd-refactor.md, с тестами по каждому слою,
плюс фиксы багов из CLAUDE.md (пункт 2), кроме перевода — он не трогается.

## Что осознанно вне рамок

- Перевод (`googletrans`) — переносится как есть, без переработки нестабильности.
- `copyright` в подписи APOD, день рождения, GIF/таймлапс EPIC — отдельные TZ
  и ветки после этого шага.
- CI/CD, структурированное логирование — вне скоупа (CLAUDE.md).
- Alembic/миграции схемы — не сейчас (см. «Решения»).
