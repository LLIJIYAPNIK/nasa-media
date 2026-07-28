# TZ-inline-mode.md — inline-режим

## Цель

Реализовать пункт 11 текущего фокуса: сейчас поделиться контентом бота можно
только пересылкой сообщения (получатель видит "Forwarded from" и должен сам
зайти в бота, чтобы получить что-то новое). Inline-режим (`@bot_username
запрос` прямо в поле ввода любого чата) — canonical способ в Telegram
распространять контент без пересылки: получатель видит готовый
пост/картинку, отправленную от имени того, кто её выбрал, не бота. Это не
новый контент, а новый канал распространения уже существующего — самая
"инфраструктурная" фича из всего набора, поэтому и последняя по
рекомендованному порядку: чем больше стабильного кешированного контента уже
есть (APOD, EPIC, дайджест, итоги недели), тем полезнее inline-режим.

## Организационная предпосылка (не код)

Inline-режим должен быть включён для бота через @BotFather
(`/setinline`) — это ручная настройка бота, не часть кода репозитория.
Явно фиксирую здесь, чтобы не потерялось: без этого шага код ниже не
заработает, сколько бы его ни было.

## Решения по неоднозначностям

- **Технический барьер: кешируется `message_id`, а Telegram inline-результаты
  с готовым медиа (`InlineQueryResultCachedPhoto`/`InlineQueryResultCachedGif`)
  требуют `file_id`, не `message_id`.** Это разные идентификаторы: `message_id`
  ссылается на сообщение в конкретном чате (годится для `copy_message`),
  `file_id` — на сам загруженный в Telegram файл (годится для мгновенной
  вставки в inline-результат без повторной загрузки). Сейчас
  `CachedMessageRef` (`application/media/ports.py`) хранит только
  `message_id` — для inline-режима этого недостаточно.
- **Расширяем `CachedMessageRef` полем `file_id: str | None = None`**, не
  заводим отдельную сущность. `TelegramAdminChatGateway._publish_single/
  _publish_animation/_publish_generated_image` уже получают `Message` в ответ
  от `bot.send_photo`/`send_animation` — просто дополнительно читают
  `message.photo[-1].file_id` / `message.animation.file_id` соответственно и
  прокидывают в `CachedMessageRef`. Ничего не публикуется по-новому, только
  дополнительно сохраняется то, что Telegram и так возвращал, но раньше
  игнорировалось.
- **Схема БД: `file_id` в каждую таблицу кеша.** `ApodModel`, `EpicDayModel`,
  `DigestModel`, `WeeklyHighlightModel` (`infrastructure/db/models.py`)
  получают `file_id: Mapped[str | None] = mapped_column(default=None)`.
  Существующие `*Repository.save()`/`get_by_date()` прокидывают это поле в обе
  стороны, как и остальные. Для строк, сохранённых до этой фичи, `file_id`
  будет `NULL` — обрабатывается веткой ниже, не требует бэкфилла/миграции
  данных (реальных пользователей в проде ещё нет, см. прецедент в
  `TZ-gif-timelapse.md`).
- **Если `file_id` неизвестен (`NULL`) — inline-результат текстовый
  (`InlineQueryResultArticle`), не отказ.** Не хотим, чтобы старые кешированные
  записи были недоступны через inline, пока их не запросят обычным способом
  и не пересохранят с `file_id`. Текстовый результат с `InputTextMessageContent`
  — не идеален, но рабочий fallback, а не ошибка пользователю.
- **Что показываем по каким запросам.** Простой префиксный разбор текста
  inline-запроса (`inline_query.query`, регистронезависимо):
  - `apod` или пусто → APOD за сегодня (кеш существующей `DeliverMediaForDate`
    для APOD, `date.today()`).
  - `epic` → EPIC-анимация за сегодня.
  - `digest`/`сводка` → дайджест за сегодня.
  - `неделя`/`week` → итоги недели.
  Дата в inline-запросе не парсится (в отличие от основного меню бота, где
  можно выбрать произвольную дату) — inline-режим специально ограничен
  "сегодня/эта неделя", чтобы не тащить туда FSM-сценарии выбора дат, которые
  не имеют смысла в контексте инлайн-строки без диалога.
- **Если по запрошенному ключу нет кеша на сегодня — inline-результат не
  запускает `fetch_and_cache` "вживую".** `answer_inline_query` ограничен по
  времени ответа Telegram (несколько секунд) — синхронно ходить в NASA API +
  собирать GIF/карточку внутри обработчика inline-запроса рискует не
  уложиться и просто не показать результатов пользователю. Если кеша нет —
  возвращается один результат-заглушка ("Ещё не готово, загляните в бота
  напрямую") вместо пустого списка. Реальное построение контента остаётся
  только через обычные сценарии (кнопки, суточная рассылка) — inline
  раздаёт уже готовое, не строит новое.
- **`cache_time` у `answer_inline_query` — 300 секунд.** Контент, который
  раздаёт inline-режим, обновляется не чаще раза в сутки (или раза в неделю)
  — Telegram может кешировать результат на своей стороне на приемлемое время,
  не нужно нулевое значение (означало бы "не кешируй вообще", лишняя
  нагрузка на бота при популярных запросах).
- **Новый тонкий роутер, не расширение существующих.** `presentation/
  telegram/routers/inline_router.py` — `build_inline_router(apod_repo,
  epic_repo, digest_repo, weekly_repo) -> Router` с одним хендлером
  `@router.inline_query()`. Не переиспользует `apod_router`/`digest_router`
  (те построены вокруг `CallbackQuery`/`Message`, не `InlineQuery` — общий
  код между ними — это уже существующие репозитории, не сами роутеры).

## Целевые файлы

```
application/media/ports.py — CachedMessageRef.file_id: str | None = None.

infrastructure/telegram/admin_chat_gateway.py — _publish_single/_publish_animation/
  _publish_generated_image прокидывают file_id в CachedMessageRef.

infrastructure/db/models.py — file_id колонка в ApodModel, EpicDayModel,
  DigestModel, WeeklyHighlightModel.

infrastructure/db/repositories.py — все *Repository.save()/get_by_date()
  учитывают file_id.

domain/media/entities.py, domain/digest/entities.py — ApodEntry, EpicDay,
  DigestEntry, WeeklyHighlightEntry получают file_id: str | None = None.

presentation/telegram/routers/inline_router.py — build_inline_router(...),
  разбор query по префиксу, InlineQueryResultCachedPhoto/CachedGif при наличии
  file_id, InlineQueryResultArticle как fallback без него и как заглушка "ещё
  не готово".

main.py — dp.include_router(build_inline_router(apod_repo, epic_repo,
  digest_repo, weekly_repo)).
```

## Тестирование

- `tests/infrastructure/test_repositories.py` — `file_id` сохраняется и
  читается обратно на всех четырёх репозиториях; `NULL` не ломает чтение уже
  существующих записей без него.
- `tests/infrastructure/test_admin_chat_gateway.py` — `_publish_single`/
  `_publish_animation`/`_publish_generated_image` возвращают `CachedMessageRef`
  с заполненным `file_id` из фейкового `Message`.
- `tests/presentation/test_inline_router.py` — по одному сценарию на каждый
  префикс запроса (`apod`/`epic`/`digest`/`неделя`), сценарий "кеша ещё нет
  на сегодня" → заглушка, сценарий "кеш есть, но без file_id" (старая запись)
  → текстовый результат вместо `CachedPhoto`.

## Что реализовано

`file_id` фиксируется при каждой публикации в admin-чат и используется inline-
режимом, чтобы моментально возвращать уже готовый контент (APOD, EPIC,
дайджест, итоги недели) в любой чат без захода в бота — с текстовым fallback
для записей без сохранённого `file_id` и без синхронного похода в NASA API
внутри обработчика inline-запроса.

## Что осознанно вне рамок

- Произвольная дата в inline-запросе — только "сегодня"/"эта неделя", см.
  «Решения».
- "Живая" сборка контента по inline-запросу при отсутствии кеша — не делаем,
  ограничение по времени ответа Telegram (см. «Решения»).
- Бэкфилл `file_id` для уже существующих кешированных записей — не нужен, в
  проде ещё нет данных, требующих миграции (см. прецедент `TZ-gif-timelapse.md`).
- Персонализация inline-результатов под пользователя, сделавшего запрос —
  контент одинаков для всех, как и в остальных фичах кеша.
