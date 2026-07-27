# TZ-ddd-refactor.md — целевая DDD-архитектура ядра бота

## Цель

Зафиксировать целевые сущности, use-case'ы и границы слоёв **до** переноса
кода APOD/EPIC из `NasaAPI-bot-skillbox-diploma` в `nasa-media` (пункт 5
текущего фокуса в CLAUDE.md). Сам перенос кода и известные баги (пункт 2)
делаются отдельной веткой/PR поверх этой структуры — здесь фиксируется только
раскладка и решения по неоднозначностям, без реализации.

Источник для логики — старый репозиторий (прочитан целиком через GitHub API):
`main.py`, `aiogram_run.py`, `config.py`, `database/*`, `handlers/APOD/*`,
`handlers/EPIC/*`, `handlers/start_handler.py`, `keyboards/inline/*`. Логика
переносится осмысленно, файлы не копируются как есть.

## Что делает старый код сейчас (для справки)

Общий паттерн для обоих источников:

1. Пользователь запрашивает медиа за дату (сегодня / конкретная дата / диапазон
   до 5 дней — только у APOD).
2. Если в БД уже есть `message_id` за эту дату — сообщение копируется/пересылается
   пользователю из admin-чата (`bot.copy_message` для APOD, повторная отправка
   `file_id`'ов через `send_media_group` для EPIC).
3. Если нет — данные запрашиваются у NASA API, публикуются в admin-чат (одно
   фото с подписью для APOD; медиа-группа без подписи для EPIC), `message_id`
   (APOD) или список `file_id` (EPIC, хранится как строка через пробел)
   сохраняется в БД, и уже из admin-чата материал уходит пользователю.
4. Раз в сутки (`periodic_update_dates` в `aiogram_run.py`) — обновление списка
   доступных дат EPIC (`fill_db.update_dates`) и рассылка сегодняшнего медиа
   всем подписанным пользователям обоих источников.
5. Подписка/отписка — идентичная логика, продублированная в
   `handlers/APOD/subscribe.py` и `handlers/EPIC/subscribe.py`: читает
   `Users` по `chat_id`, переключает булево поле, отвечает пользователю.

Расхождения источников: APOD переводит заголовок/описание (`googletrans`) и
собирает подпись; EPIC подписи не имеет, но качает N кадров и умеет собирать их
в медиа-группу. APOD ограничен `APOD_LOWER_BOUND` из конфига; EPIC — жёстко
зашитой датой `2015-06-13`.

## Целевые слои

```
domain/            — чистые правила, без I/O
application/        — use-case'ы, зависят только от портов (protocols)
infrastructure/      — реализация портов: БД, NASA API, Telegram, файлы, перевод
presentation/telegram/ — aiogram-роутеры, тонкие
main.py              — composition root: собирает конкретные реализации и стартует бота
```

Направление зависимостей: `presentation` и `infrastructure` зависят от
`application`/`domain` (через порты), обратной зависимости нет.
`presentation/web` (когда дойдёт очередь, вне скоупа сейчас) будет вызывать те
же `application`-сервисы, не касаясь остального.

### domain

- `domain/media/entities.py`
  - `ApodEntry` — `date`, `message_id`, `copyright: str | None` (поле уже
    закладывается в сущность сейчас, т.к. это данные NASA API; сама фича
    атрибуции — TZ-copyright.md, отдельно и позже).
  - `EpicDay` — `date`, `frames: list[EpicFrame]` (агрегат, а не
    пробел-разделённая строка, см. «Решения» ниже).
  - `EpicFrame` — `telegram_file_id`, `position`.
- `domain/users/entities.py`
  - `User` — `chat_id`, `apod_subscribed: bool`, `epic_subscribed: bool`,
    методы `is_subscribed(source: MediaSourceKind)` /
    `with_subscription(source, value)` — чтобы application-слой не знал про
    конкретные имена полей.
- `domain/media/value_objects.py`
  - `MediaSourceKind` (enum: `APOD`, `EPIC`)
  - `DateRange` — валидирует `start <= end <= today` и `end - start <= 5 дней`
    (правило APOD «несколько дат»).
  - Правило нижней границы даты на источник (`APOD_LOWER_BOUND` из конфига,
    `2015-06-13` для EPIC) — как чистая функция/метод, без обращения к
    `config.py` напрямую (границы приходят снаружи как параметр).
- `domain/media/exceptions.py` — `MediaNotAvailable` (замена текущему
  `except KeyError`/широкому `except Exception`).

Никакого I/O, SQLAlchemy, aiohttp, aiogram в этом слое.

### application

Ключевое архитектурное решение — **один use-case на доставку медиа**,
параметризованный портом источника, а не два похожих юзкейса под APOD/EPIC:

- `application/media/ports.py`
  - `MediaProvider(Protocol)` — `async def fetch(date) -> MediaPayload`
    (кидает `MediaNotAvailable`). Реализуют `ApodProvider`, `EpicProvider` в
    infrastructure — вся специфика (перевод для APOD, скачивание N кадров для
    EPIC) прячется внутри конкретной реализации, наружу — единый контракт.
  - `AdminChatGateway(Protocol)` — `publish(payload) -> CachedMessageRef`,
    `forward_cached(ref, chat_id) -> None`. Один порт на оба источника: и
    «отправить фото с подписью», и «отправить медиа-группу» реализуют один и
    тот же протокол через разные методы `MediaPayload` (см. ниже), не разные
    гейтвеи.
  - `ApodRepository` / `EpicRepository` / `UserRepository` (Protocols) —
    `get_by_date`, `save`, и т.п.
- `application/media/deliver_media.py`
  - `DeliverMediaForDate(provider, repo, gateway)` — один use-case: чек кеша →
    если есть, `forward_cached` → если нет, `provider.fetch` → `gateway.publish`
    → `repo.save` → `forward_cached`. Используется и для одиночного запроса, и
    (в цикле по датам) для APOD-диапазона, и для рассылки.
- `application/media/broadcast.py`
  - `BroadcastSubscribedUsers(source, deliver_use_case, user_repo)` — читает
    подписанных пользователей и для каждого вызывает `DeliverMediaForDate` на
    сегодняшнюю дату. Заменяет продублированные
    `subscribe_apod_send_message`/`subscribe_send_message`.
- `application/subscriptions/manage_subscription.py`
  - `SetSubscription(user_repo, chat_id, source: MediaSourceKind, value: bool)`
    — один use-case вместо `handlers/APOD/subscribe.py` +
    `handlers/EPIC/subscribe.py`.
- `application/users/register_user.py`
  - `GetOrCreateUser(user_repo, chat_id)` — логика из `start_handler.py`.
- `application/epic/refresh_availability.py`
  - `RefreshEpicAvailability(epic_index_port, epic_repo)` — замена
    `fill_db.update_dates`. Специфично для EPIC (у APOD нет аналога — доступность
    даты определяется только границами, не списком с NASA), поэтому это не часть
    общего медиа-юзкейса, а отдельный сценарий.

`MediaPayload` — простой DTO (не Entity): либо «одно изображение + подпись»
(APOD), либо «список изображений без подписи» (EPIC); `AdminChatGateway.publish`
переключается по его форме, а не по флагу источника — так подпись/атрибуция
(будущий copyright) собирается один раз в момент формирования `MediaPayload`
внутри `ApodProvider`, и это единственное место, которое тронет TZ-copyright.md.

### infrastructure

- `infrastructure/db/` — SQLAlchemy-модели (`ApodModel`, `EpicModel`,
  `EpicFrameModel` как отдельная таблица с FK на `EpicModel` — не строка через
  пробел, см. «Решения»), `UserModel`, async engine/session, репозитории,
  реализующие `*Repository` протоколы.
- `infrastructure/nasa/` — `apod_client.py`, `epic_client.py` на `aiohttp`
  (закрывает баг с блокирующим `requests.get` в `current_date()`), реализуют
  `MediaProvider`.
- `infrastructure/telegram/admin_chat_gateway.py` — единственная реализация
  `AdminChatGateway` на aiogram `Bot`, общая для APOD и EPIC (устраняет
  дублирование `handlers/APOD/tools/sender.py` /
  `handlers/EPIC/tools/send_photo.py` + `await_message.py`).
- `infrastructure/translation/` — обёртка над `googletrans`, поведение не
  меняется (перевод вне скоупа сейчас).
- `infrastructure/files/temp_file.py` — временные файлы с `uuid4()`-суффиксом
  вместо фиксированного `temp_image.jpg` (закрывает баг с гонкой при
  параллельных запросах).

### presentation/telegram

- Роутеры (`apod_router.py`, `epic_router.py`, `start_router.py`) — только
  разбор апдейта/состояния FSM и вызов application-сервисов, без прямых
  обращений к `requests`/`aiohttp`/файловой системе (сейчас это нарушается в
  `start_end_dates.py`, `await_date_data.py` и др.).
- `presentation/telegram/keyboards/` — как есть сейчас, без изменений в логике.
- `presentation/telegram/states.py` — FSM-состояния (`Form`, `CurrentDateForm`
  и т.п.), без изменений в наборе состояний.

## Решения по неоднозначностям

- **Один use-case доставки медиа вместо двух.** Причина — APOD и EPIC уже
  сегодня дублируют идентичный поток «кеш → NASA → admin-чат → пользователь»
  (см. CLAUDE.md, «Не дублировать код»). Различие вынесено в `MediaProvider`
  (что и как скачивается) и форму `MediaPayload` (фото с подписью vs группа без
  подписи), а не в отдельные юзкейсы.
- **EPIC-кадры как таблица `EpicFrame`, а не строка через пробел.** Старая
  схема (`message_id = " ".join(file_ids)`) требует парсинга строки при каждом
  чтении и не имеет отдельного места для будущего `gif_message_id` (задача 1,
  GIF/таймлапс). Нормализованная таблица кадров + отдельная колонка под GIF
  добавляется позже, в TZ-gif-timelapse.md, самой миграцией — сейчас закладывается
  только структура кадров, чтобы её не пришлось перекраивать заново под GIF.
- **Подписка — два явных булевых поля на `User`, не универсальная N-источников
  таблица.** Источника сейчас два (APOD/EPIC), Mars Rover/NeoWs — только
  бэклог идей, не подтверждённая задача. Обобщение до N источников без факта
  третьего источника было бы преждевременной абстракцией (см. принцип «не
  проектировать под гипотетическое будущее» в CLAUDE.md). Дублирование самого
  use-case'а (`subscribe.py` под каждый источник) убирается через
  `SetSubscription(source: MediaSourceKind, ...)` — этого достаточно.
- **`copyright` и день рождения закладываются в сущности сейчас (пустое поле),
  но не проектируются.** `ApodEntry.copyright` и место в `User` под будущую
  дату рождения — просто зарезервированное расширение, чтобы TZ-copyright.md и
  TZ-birthday.md не начинались с миграции самой сущности. Логика (что делать с
  `copyright` в подписи, когда слать поздравление) — предмет отдельных TZ,
  здесь не решается.
- **Судьба `AsyncIOScheduler`, точный список зависимостей `pyproject.toml`,
  сужение `except Exception` — не решаются в этой TZ.** Это предмет TZ для
  шага «перенос ядра + известные баги» (пункт 2 CLAUDE.md), а не архитектурной
  раскладки: они про конкретную реализацию, не про границы слоёв.

## Тестирование по слоям

- `domain` — юнит-тесты без моков, чистые функции/сущности.
- `application` — юнит-тесты на use-case'ах с фейковыми/in-memory реализациями
  портов (`FakeApodProvider`, `InMemoryUserRepository` и т.п.), без реальной БД
  и сети.
- `infrastructure` — точечные интеграционные тесты (репозитории — против
  тестовой БД/SQLite in-memory; HTTP-клиенты — с замоканными ответами NASA API).
- `presentation` — тонкий слой, тестируется через application-тесты плюс
  минимальные тесты роутинга (правильный use-case вызван с правильными
  параметрами по нужному callback_data/состоянию).

## Что реализовано этой TZ

Только документ — раскладка пакетов, протоколы портов (сигнатуры), сущности и
их поля перечислены выше как контракт. Сам код (миграция логики из старого
репозитория, тесты, `pyproject.toml`) — в ветке «перенос ядра» по отдельной TZ
для этого шага, поверх структуры папок, которую создаёт бутстрап-ветка.

## Что осознанно вне рамок

- Реализация GIF/таймлапс, атрибуции copyright, дня рождения — свои TZ и ветки
  после того, как ядро перенесено на эту структуру.
- `presentation/web` — свой `TZ-web.md`, когда дойдёт очередь (см. CLAUDE.md,
  «Статус проекта»).
- Переработка перевода (`googletrans`) — вне скоупа по CLAUDE.md.
- Решение по `AsyncIOScheduler` (использовать или убрать) и точная стратегия
  сужения `except Exception` — решаются в TZ для шага «перенос ядра».
- CI/CD и структурированное логирование — вне скоупа (CLAUDE.md).
