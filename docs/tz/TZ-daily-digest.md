# TZ-daily-digest.md — Сводка за сегодня

## Цель

Реализовать пункт 6 текущего фокуса из CLAUDE.md: третий тип контента после
APOD/EPIC — краткая ежедневная сводка из трёх источников (космическая погода,
ближайший астероид, заметное событие на Земле) плюс ссылка на уже
закешированный APOD дня. Растит вовлечённость без привязки к конкретной дате,
которую вводит пользователь — просто «что нового сегодня».

## Используемые API

Проверено живыми запросами 27–28 июля 2026 (см. обсуждение в чате, не
выдумано):

- **DONKI**, `GET {NASA_DONKI_URL}` (`startDate=endDate=сегодня`, `type=all`,
  `api_key=NASA_API_KEY` — тот же ключ, что у APOD/EPIC, новый секрет не
  нужен). Отдаёт плоский список уведомлений с полями `messageType`
  (`CME`/`FLR`/`GST`/`RBE`/`IPS`/`Report`/...) и `messageIssueTime`.
- **NeoWs**, `GET {NASA_NEOWS_URL}` (`start_date=end_date=сегодня`, тот же
  `api_key`). Отдаёт `near_earth_objects[<дата>]` — список астероидов с
  размером, `miss_distance` (км/лунные дистанции) и
  `is_potentially_hazardous_asteroid`.
- **EONET**, `GET {NASA_EONET_URL}` (`status=open`, `limit=N`). **Отдельный
  хост (`eonet.gsfc.nasa.gov`), `api_key` не принимает и не требует вообще** —
  важно не передавать туда `NASA_API_KEY` по аналогии с остальными клиентами.
  Не поддерживает фильтр по дате на уровне API (в отличие от DONKI/NeoWs) —
  берём N последних открытых событий, «свежесть» выбираем сами доменным
  правилом.
- **APOD** — переиспользуется `ApodRepository` (уже существующий порт из
  `application/media/ports.py`), новый клиент не пишется. Если APOD за
  сегодня ещё не закеширован (`get_by_date` вернул `None`) — сводка просто не
  включает строку про картинку дня, ничего не выдумываем и не ждём.

Явно НЕ используются: **InSight** (при живой проверке эндпоинт вернул пустой
ответ — согласуется с завершением миссии в декабре 2022, полагаться на неё
нельзя), **Mars Rover Photos** и остальные 10 API из общего каталога —
статичные каталоги без привязки к дате либо отдельные будущие фичи, не про
дайджест.

## Что уже есть и на что это опирается

Текущий медиа-конвейер (`TZ-core-transfer.md`, `TZ-gif-timelapse.md`) устроен
как: `MediaSourceAdapter` (Protocol в `application/media/source_adapters.py`)
с тремя методами `get_cached`/`fetch_and_cache`/`forward_cached`, за которым
прячется специфика конкретного источника, и один общий use-case
`DeliverMediaForDate` (`application/media/deliver_media.py`), который этот
Protocol дёргает: кеш → NASA → admin-чат → пользователь. `AdminChatGateway`
(`application/media/ports.py` + `infrastructure/telegram/admin_chat_gateway.py`)
умеет публиковать `MediaPayload` (сейчас — `SinglePhotoPayload | AnimationPayload`)
и пересылать закешированное сообщение через `bot.copy_message`.
`BroadcastSubscribedUsers` (`application/media/broadcast.py`) — общий класс
рассылки, параметризованный `MediaSourceKind`, дергается из `periodic_broadcast`
в `main.py` для APOD и EPIC.

Дайджест — не фото и не анимация, а текст, но кешируется и пересылается по
тому же принципу (одно сообщение на дату, `copy_message` всем остальным).
Поэтому решение ниже — не новая параллельная инфраструктура, а расширение уже
существующей на один новый вариант пейлоада и один новый адаптер, подключаемый
к уже существующим `DeliverMediaForDate`/`BroadcastSubscribedUsers` без
изменений в них.

## Решения по неоднозначностям (с обоснованием)

- **Новый вариант пейлоада `TextPayload(text: str)`, а не отдельный
  гейтвей.** `AdminChatGateway.publish()` уже задуман как общий контракт
  «опубликуй и получи `CachedMessageRef`», а не «опубликуй фото». Добавляю
  `TextPayload` в объединение `MediaPayload` (`application/media/ports.py`)
  и ветку `_publish_text` в `TelegramAdminChatGateway.publish()`
  (`infrastructure/telegram/admin_chat_gateway.py`) — просто
  `bot.send_message(admin_chat_id, payload.text)`, без скачивания/временных
  файлов. Заводить второй `AdminChatGateway` под текст — плодить копию того
  же самого паттерна кеширования, чего явно нельзя по инженерным принципам
  CLAUDE.md.
- **`DigestSourceAdapter` реализует существующий `MediaSourceAdapter`
  Protocol — новый use-case не пишется.** `DeliverMediaForDate` уже не знает
  ничего специфичного про APOD/EPIC, только вызывает три метода адаптера —
  значит `DigestSourceAdapter` с той же сигнатурой подключается к нему
  напрямую. Экономит не архитектурный слой, а конкретно необходимость
  тестировать ещё один «кеш → NASA → admin-чат → пользователь» с нуля — он
  уже протестирован на APOD/EPIC.
- **`fetch_and_cache` дёргает три клиента параллельно
  (`asyncio.gather`)** — тот же приём, что уже применяется в
  `ApodProvider.fetch()` для двух переводов и в `EpicProvider.fetch()` для
  кадров. Плюс синхронное (не сетевое) чтение уже закешированного APOD через
  `ApodRepository.get_by_date()` — если его ещё нет, просто `None`, без
  дополнительного запроса к NASA.
- **DONKI: не парсим детали (скорость CME, класс вспышки) из
  `messageBody`.** Это неструктурированный текст на английском, формат
  которого не задокументирован и может незаметно поменяться на стороне NASA
  (живой пример — многостраничный текстовый отчёт с ссылками на анимации).
  Использую только `messageType` и `messageIssueTime` — то есть домен видит
  `SpaceWeatherHighlight(message_type: str, issued_at: datetime)`, не сырой
  текст. Смысловая строка в сводке собирается по `messageType` через свой
  русский шаблон, не переводом/пересказом `messageBody`.
- **Приоритет для «главного» события DONKI: `GST` > `FLR` > `CME` > `IPS` >
  `RBE`, `Report` игнорируется.** `Report` — еженедельный сводный
  мета-документ (не событие конкретного дня, приходит по средам), включать
  его в подборку «главного события за сегодня» бессмысленно. Если за день
  несколько уведомлений одного типа — берём самое позднее по
  `messageIssueTime`. Если подходящих уведомлений нет вообще — доменная
  функция возвращает `None`, текстовый шаблон подставляет «Космос сегодня
  спокоен».
- **NeoWs: берём один астероид — с минимальной дистанцией пролёта**, не все
  пять из живого теста. Дистанция сравнивается в километрах
  (`miss_distance.kilometers`, приводится к `float` в клиенте — NASA отдаёт
  строкой). В строку идёт диаметр (min–max, округлённый до целых метров) и
  дистанция в лунных расстояниях, плюс пометка, если
  `is_potentially_hazardous_asteroid`. Если список за день пуст — «Заметных
  астероидов сегодня нет».
- **EONET: берём одно самое свежее событие**, не список. «Свежесть» — по
  максимальной дате среди `geometry[].date` события (у события может быть
  несколько точек геометрии с разными датами, как в живом тесте с тропическим
  штормом — берём последнюю). Если список пуст (в реальности почти никогда,
  но клиент может вернуть `[]`) — «Заметных событий на Земле сегодня нет».
- **`NaturalEventClient` не принимает `day` в сигнатуре, в отличие от двух
  других портов.** EONET не поддерживает точную фильтрацию по дате на уровне
  API (см. «Используемые API» выше) — `fetch_recent() -> Sequence[EarthEventHighlight]`
  честно отражает это ограничение вместо того, чтобы притворяться
  днём-параметром, который ни на что не влияет.
- **Кеш — `DigestModel(date unique, message_id unique)`**, отдельная таблица
  `daily_digest`, дословно повторяющая форму `ApodModel`. Не переиспользую
  `ApodModel`/таблицу `apod` — семантически разные сущности (одна — конкретная
  картинка, другая — сводка), даже если форма схемы совпадает.
- **День — `date.today()`, без специальной обработки часового пояса.** Это
  уже сложившееся поведение проекта: `periodic_broadcast`, проверка дня
  рождения и кнопка «Сегодня» у APOD одинаково используют `date.today()` без
  явного часового пояса (в отличие от унаследованного из старого репозитория
  `AsyncIOScheduler(timezone="Europe/Moscow")`, от которого сознательно
  отказались — см. `TZ-core-transfer.md`). Вводить особый часовой пояс только
  для дайджеста значило бы разойтись с остальным проектом без причины.
- **Ошибка `MediaNotAvailable` дайджестом не бросается.** В отличие от
  APOD/EPIC (нет данных за дату = реальная ошибка), у дайджеста по
  конструкции всегда есть что сказать — либо у источника есть данные, либо
  подставляется явная фраза «сегодня без заметных событий». Значит
  `apod_router`-стиль `try/except MediaNotAvailable` вокруг
  `deliver_digest.execute(...)` в роутере не нужен: настоящая сетевая ошибка
  просто всплывает необработанной, как и договаривались в
  `TZ-gif-timelapse.md` для сбоя сборки GIF.
- **Подписка — третье значение `MediaSourceKind.DIGEST`, третье поле
  `User.digest_subscribed`.** Текущие `User.is_subscribed`/`with_subscription`
  — тернарник на два источника (`domain/users/entities.py:16-22`), на три он
  уже не масштабируется читаемо. Меняю на словарь
  `{MediaSourceKind.APOD: "apod_subscribed", ...}` + `getattr`/
  `dataclasses.replace(self, **{field: value})` — заодно готово для
  четвёртого источника, если такой появится, без повторной правки этого
  метода. Аналогично `SqlAlchemyUserRepository.list_subscribed()`
  (`infrastructure/db/repositories.py:88-91`) — тернарник колонки меняется на
  такой же словарь.
- **Подписка переиспользует `register_subscribe_handlers`
  (`presentation/telegram/subscribe_handler.py`) — не пишется отдельный
  хендлер.** Добавляю `MediaSourceKind.DIGEST: "сводки"` в `_LABELS`. Текст
  получается «Вы подписались на рассылку сводки» / «Вы отписались от
  рассылки сводки» — грамматически не идеально ровно (для APOD/EPIC это
  просто имя источника, для дайджеста — уже родительный падеж), но
  переиспользование одного маленького генерического хендлера важнее
  идеальной грамматики одной строки; если не понравится на практике —
  поменять `_LABELS[DIGEST]` тривиально.
- **UX — кнопка «Сводка» в стартовом меню открывает подраздел**, как APOD и
  EPIC, а не сразу шлёт сводку. Подраздел (`digest_kb.py`): «Показать сводку»
  (`digest_show`) + подписка/отписка + «Назад». Единообразно с уже
  существующим паттерном вместо третьего UX-паттерна в одном боте.

## Целевые файлы

```
domain/digest/value_objects.py — SpaceWeatherHighlight(message_type, issued_at),
  AsteroidHighlight(name, diameter_min_m, diameter_max_m, miss_distance_km,
  miss_distance_lunar, is_hazardous), EarthEventHighlight(title, category,
  event_date).

domain/digest/entities.py — DigestEntry(date, message_id), форма как ApodEntry.

domain/digest/digest_text.py — чистые функции без I/O:
  pick_significant_space_weather(events) -> SpaceWeatherHighlight | None,
  pick_closest_asteroid(asteroids) -> AsteroidHighlight | None,
  pick_latest_earth_event(events) -> EarthEventHighlight | None,
  build_digest_text(day, space_weather, asteroid, earth_event, apod_cached) -> str.

application/digest/ports.py — SpaceWeatherClient.fetch_for_day(day),
  NearEarthObjectClient.fetch_for_day(day), NaturalEventClient.fetch_recent(),
  DigestRepository.get_by_date/save (форма как ApodRepository).

application/digest/source_adapter.py — DigestSourceAdapter, реализует
  MediaSourceAdapter из application/media/source_adapters.py.

application/media/ports.py — добавить TextPayload в MediaPayload.

infrastructure/telegram/admin_chat_gateway.py — ветка _publish_text.

infrastructure/nasa/donki_client.py, neows_client.py, eonet_client.py —
  по одному клиенту на источник, минимальный парсинг в *Highlight-объекты.

infrastructure/db/models.py — DigestModel (таблица daily_digest);
  UserModel.digest_subscribed: Mapped[bool] = mapped_column(default=False).

infrastructure/db/repositories.py — SqlAlchemyDigestRepository (форма как
  SqlAlchemyApodRepository); SqlAlchemyUserRepository — digest_subscribed в
  save()/_to_domain(), словарь колонок в list_subscribed().

domain/users/entities.py — User.digest_subscribed: bool = False;
  is_subscribed/with_subscription через словарь полей вместо тернарника.

presentation/telegram/keyboards/start_kb.py — кнопка «Сводка» (callback_data="digest").

presentation/telegram/keyboards/digest_kb.py — get_digest_kb(is_subscribed):
  «Показать сводку» / подписка / «Назад».

presentation/telegram/routers/digest_router.py — build_digest_router(deliver_digest,
  set_subscription, get_or_create_user): "digest" открывает подменю,
  "digest_show" вызывает deliver_digest.execute(date.today(), chat_id) под
  ChatActionSender.typing (не upload_photo — это текст); register_subscribe_handlers
  с MediaSourceKind.DIGEST.

presentation/telegram/subscribe_handler.py — _LABELS[MediaSourceKind.DIGEST] = "сводки".

domain/media/value_objects.py — MediaSourceKind.DIGEST = "digest".

config.py, .env.example — NASA_DONKI_URL, NASA_NEOWS_URL, NASA_EONET_URL
  (не секреты, публичные эндпоинты — как NASA_APOD_URL/NASA_EPIC_URL сейчас).

main.py — сборка трёх новых клиентов и digest_repo, DigestSourceAdapter,
  deliver_digest, broadcast_digest = BroadcastSubscribedUsers(MediaSourceKind.DIGEST,
  deliver_digest, user_repo) — добавляется в periodic_broadcast(...) наравне с
  broadcast_apod/broadcast_epic; dp.include_router(build_digest_router(...)).
```

## Тестирование

- `tests/domain/test_digest_text.py` — `pick_*` функции на «есть один
  подходящий», «есть несколько — выбирается правильный по приоритету/дате/
  дистанции», «список пуст → None»; `build_digest_text` на все восемь
  комбинаций (космос/астероид/земля/apod каждый — есть или нет).
- `tests/infrastructure/test_nasa_clients.py` — по образцу существующих
  тестов `ApodProvider`/`EpicProvider` через `FakeClientSession`: DONKI —
  парсинг списка уведомлений и фильтрация `Report`; NeoWs — парсинг
  `near_earth_objects[<дата>]`, пустой день; EONET — парсинг событий,
  подтверждение, что запрос **не содержит** `api_key` в параметрах.
- `tests/application/test_digest_source_adapter.py` — по образцу
  `test_source_adapters.py`: `get_cached` хит/промах, `fetch_and_cache`
  публикует `TextPayload` и сохраняет `DigestEntry`, `forward_cached`
  зовёт `gateway.forward_single`. Новые фейки в `tests/application/fakes.py`:
  `FakeSpaceWeatherClient`, `FakeNearEarthObjectClient`, `FakeNaturalEventClient`,
  `FakeDigestRepository`.
- `tests/domain/test_user_entity.py` — расширить сценариями подписки на
  `MediaSourceKind.DIGEST` (регрессия: APOD/EPIC подписки не должны
  сломаться при переходе с тернарника на словарь).
- `tests/infrastructure/test_repositories.py` — `list_subscribed(DIGEST)`,
  `save`/`_to_domain` с `digest_subscribed`.
- `tests/presentation/test_digest_router.py` — по образцу
  `test_epic_router.py`: подписка/отписка через параметризованный тест,
  `digest_show` вызывает `deliver_media.execute` с сегодняшней датой.

## Что реализовано

Полный вертикальный срез: три новых NASA-клиента → доменные правила выбора
и сборки текста → `DigestSourceAdapter` поверх существующего `DeliverMediaForDate`
→ кеш в отдельной таблице → кнопка и подписка в Telegram, встроенная в
существующий суточный цикл рассылок.

## Что осознанно вне рамок

- Персонализация под пользователя (например, EONET-события по геолокации) —
  сводка одинакова для всех, как и было решено раньше.
- Другие источники (Mars Rover Photos, SSD/CNEOS fireballs и т.п.) —
  отдельные будущие фичи, не часть этой сводки.
- Перевод/локализация формулировок NASA — не нужна благодаря шаблонному
  подходу (используются только структурированные поля, не `messageBody`),
  поэтому фича не зависит от `googletrans` вообще.
- Автоматический повторный подсчёт «главного» события DONKI при появлении
  новых уведомлений в течение того же дня после первой публикации сводки —
  сводка кешируется один раз на дату, как и APOD/EPIC; обновлять задним
  числом не делаем.
