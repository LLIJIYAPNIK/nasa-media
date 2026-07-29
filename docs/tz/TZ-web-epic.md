# TZ-web-epic.md — веб-страница `/epic`: настоящая Земля глазами EPIC

## Цель

`/epic` сейчас — заглушка (`PLACEHOLDER_SECTIONS` в `homepage_router.py`).
Задача — первая настоящая реализация этого раздела: полноэкранная
3D-модель Земли, но не декоративная (как на главной, статичные текстуры
`Maps/*`), а построенная из настоящего сегодняшнего снимка EPIC. Ничего
кроме самой модели на странице нет — ни статистики, ни подписи, ни даты
кадра: пользователь просит именно «модель Земли на весь экран, вращать,
крутить, приближать и отдалять, на фоне чёрный цвет и звёзды» и явно
уточняет, что больше ничего не нужно.

## Что уже есть и что меняется

EPIC уже используется ботом (`infrastructure/nasa/epic_client.py` →
`EpicProvider.fetch()`): для даты качаются все кадры, из них собирается
GIF (`AnimationPayload`, см. `TZ-gif-timelapse.md`) и кешируется через
admin-чат/`EpicRepository` в БД. Этот путь — Telegram-специфичный
(персистентность в БД, `message_id`, доставка в чат) и веб его не
переиспользует — по тому же принципу, что уже зафиксирован в
`TZ-web.md` для главной страницы: веб читает данные NASA напрямую через
свой read-only `application/web/`-слой, а не через
`application/media`/admin-чат-кеш.

Ответ EPIC `.../date/{day}` при этом уже содержит на каждый кадр
`centroid_coordinates` (широта/долгота подсолнечной точки — грубо говоря,
что сейчас в центре кадра) — `EpicProvider` сейчас качает этот ответ, но
использует из него только `image`, остальное отбрасывает. Эта же
подсолнечная точка — ровно то, что нужно вебу, чтобы понять, куда
«смотрело» EPIC в момент съёмки, и повернуть модель этой стороной к
камере.

## Решения по неоднозначностям

- **Один кадр как декаль на сфере, не сшивка нескольких кадров в полную
  карту.** Обсуждались два уровня амбиции (простой и «сшить кадры за
  сутки в equirectangular-текстуру»); пользователь явно выбрал первый и
  попросил «ничего лишнего». EPIC физически видит только освещённое
  полушарие с одной точки — обратную сторону модели показываем сплошным
  тёмным цветом, а не выдуманной/декоративной текстурой: это честно
  (EPIC её не фотографировал) и не требует картографической репроекции с
  сшивкой швов между кадрами разного времени съёмки.
- **Дата — последняя известная NASA, не «сегодня».** NASA публикует EPIC
  с задержкой (иногда на сутки) — берём `max(fetch_known_dates())`
  (`EpicAvailabilityClient`, уже есть, переиспользуется как есть), а не
  `date.today()`, которая может ещё не иметь данных.
- **Кадр — средний по списку кадров дня** (`frames[len(frames)//2]`),
  простой детерминированный выбор без дополнительной эвристики (например
  «ближе к полудню по времени кадра») — не запрошено, усложнять не
  вижу смысла.
- **Проекция в шейдере — приближённая ортографическая, не точная
  картографическая репроекция.** Референс-ось (единичный вектор из
  `centroid_lat/lon`) фиксируется на сфере один раз при загрузке; в
  фрагментном шейдере кадр проецируется на видимое полушарие через
  проекцию нормали на плоскость, перпендикулярную референс-оси
  (`uv = (dot(normal, tangentU), dot(normal, tangentV))`), с плавным
  затуханием в тёмный цвет к терминатору (`smoothstep`). Это
  приближение, не точная реализация обратной ортографической проекции с
  учётом кривизны у самого края диска — для «настоящее фото, узнаваемо
  сориентированное» этого достаточно, более точная реализация — лишняя
  сложность, которую пользователь прямо просил не делать.
- **Не дублировать парсинг ответа NASA между ботом и вебом.** Общая
  часть (скачать список кадров даты, скачать байты конкретного кадра)
  выносится в новый `infrastructure/nasa/epic_frames.py`
  (`EpicFrameMeta`, `fetch_day_frames`, `fetch_frame_bytes`,
  `EPIC_ARCHIVE_BASE_URL` — переезжает сюда). `EpicProvider.fetch()`
  переписывается на эти функции вместо собственного инлайн-парсинга;
  `EPIC_ARCHIVE_BASE_URL` реэкспортируется из `epic_client.py`, чтобы не
  трогать существующий импорт в `tests/infrastructure/test_nasa_clients.py`.
  Побочный эффект: `centroid_coordinates` становится обязательным полем
  парсинга (это реальная форма ответа NASA EPIC API, не выдумка ради
  веба) — существующие фикстуры EPIC-теста дополняются этим полем.
- **Кеш — два отдельных слота, как у главной страницы, не один общий
  класс.** `EpicTextureFileCache` (диск, только байты JPEG, по образцу
  `EventMapFileCache`) и `EpicPageSnapshotCache` (in-memory TTL на один
  слот, по образцу `SnapshotCache`). Не обобщаю их в общий кэш-класс с
  уже существующими двумя — тот же принцип, что уже применён в
  `TZ-weekly-highlights.md` (`GenericSourceAdapter`): схлопывать в общую
  абстракцию имеет смысл на третьем похожем случае, когда дублирование
  неоспоримо, а не заранее. Здесь у каждого вида кэша сейчас только
  второй экземпляр (после `EventMapFileCache`/`SnapshotCache`).
- **TTL in-memory кэша — 1 час, не 300 сек, как у `SnapshotCache`.** У
  `EpicPageSnapshotCache` нет дешёвого способа проверить «not stale»
  без сетевого запроса (в отличие от `SnapshotCache.get(day)`, где `day`
  — это просто `date.today()`): дата в EPIC меняется не чаще раза в
  сутки, поэтому час — разумный компромисс между свежестью и
  количеством обращений к NASA `/all` + `/date/{day}`.
- **Разрешение текстуры — 1024×1024 JPEG**, между `640×640` у GIF
  (маленькая анимация в Telegram) и `1280×1280` у одиночного фото бота
  (`temp_file.py`) — здесь текстура на весь экран, но не нужен вес
  оригинала NASA (обычно ~2048×2048 PNG).
- **Управление — `OrbitControls` из `three/addons/`, не ручные
  pointer-обработчики.** Уже есть прецедент подключения `three` через
  `importmap` без сборщика (`homepage.html`) — тот же приём для адреса
  аддона (`"three/addons/": ".../examples/jsm/"`). Даёт вращение
  (drag), зум (колесо/pinch) и инерцию (damping) без ручной реализации.
  `enablePan = false` — пользователь просил вращать/крутить/приближать,
  панорамирование не упоминалось и только мешало бы держать Землю в
  кадре. `minDistance`/`maxDistance` ограничивают зум, чтобы нельзя было
  провалиться внутрь сферы или улететь в черноту.
- **`prefers-reduced-motion` НЕ форсирует статичный fallback здесь**, в
  отличие от `earth.js` на главной. На главной Земля сама слегка
  доворачивается за курсором постоянно (ambient-движение, от которого
  и предупреждает `prefers-reduced-motion`); здесь модель полностью
  неподвижна, пока пользователь сам не потянет/не покрутит колесо —
  это не тот вид автономного движения, которое эта настройка призвана
  подавлять. Фолбэк на статичную картинку остаётся только на случай
  реальной недоступности WebGL (как и на главной).
- **Чёрный фон и звёзды — переиспользуются как есть, ничего нового.**
  `starfield.js` (два слоя точек, мерцание) и тёмный градиент
  (`--color-bg-3: #000103` и соседние переменные в `tokens.css`) уже
  рендерятся на каждой странице через `base.html` — ровно то
  «кинематографичное» ощущение, которое просил пользователь, без
  отдельной реализации под `/epic`.
- **Нав-рейл поверх полноэкранного канваса — уже работает без
  дополнительного кода.** `.nav-rail` имеет `z-index: 5`, новый
  `.epic-mount` — `z-index: 2` (как у `.earth-mount` на главной):
  клики по иконкам навигации перехватываются раньше, чем доходят до
  канваса, конфликта drag-жестов с навигацией не будет.
- **Нет ни одной известной даты EPIC или у последней даты 0 кадров —
  показываем существующий `placeholder.html`** (текст «EPIC», как у
  прежней заглушки), а не отдельную страницу ошибки — переиспользование
  вместо нового UI ради редкого крайнего случая (NASA API недоступен).

## Целевые файлы

```
infrastructure/nasa/epic_frames.py — EPIC_ARCHIVE_BASE_URL (переезжает
  из epic_client.py), EpicFrameMeta(image, centroid_lat, centroid_lon),
  fetch_day_frames(session, api_key, api_base_url, day) -> Sequence[...],
  fetch_frame_bytes(session, api_key, day, image_name) -> bytes.

infrastructure/nasa/epic_client.py — EpicProvider.fetch() переписан на
  fetch_day_frames/fetch_frame_bytes; EPIC_ARCHIVE_BASE_URL
  реэкспортируется для обратной совместимости импорта в тестах.

infrastructure/web/epic_texture_builder.py — NasaEpicTextureBuilder:
  средний кадр дня, кеш-хит — не качает байты повторно, кеш-мисс —
  fetch_frame_bytes + ресайз до 1024×1024 JPEG (Pillow,
  asyncio.to_thread) + запись в EpicTextureFileCache; возвращает
  EpicTexture(cache_key, centroid_lat, centroid_lon) | None.

infrastructure/web/epic_texture_cache.py — EpicTextureFileCache: файловый
  кеш байт по cache_key = ISO-дата, var/cache/epic-textures/*.jpg, та же
  защита ключа регуляркой, что и в event_map_cache.py.

infrastructure/web/epic_snapshot_cache.py — EpicPageSnapshotCache:
  in-memory TTL (1 час) кэш одного слота EpicPageSnapshot.

application/web/epic_page_query.py — EpicPageSnapshot(frame_date,
  centroid_lat, centroid_lon, texture_url); протоколы EpicAvailability
  (fetch_known_dates) и EpicTextureBuilder (build(day) ->
  EpicTexture | None); GetEpicPageSnapshot.execute() -> EpicPageSnapshot
  | None.

presentation/web/routers/epic_router.py — build_epic_router(...):
  GET /epic (снапшот или get-or-compute через EpicPageSnapshotCache;
  placeholder.html при None), GET /api/epic/textures/{cache_key}.jpg
  (байты из EpicTextureFileCache, 404 при отсутствии).

presentation/web/routers/homepage_router.py — "/epic" убирается из
  PLACEHOLDER_SECTIONS.

presentation/web/app.py — подключение EpicAvailabilityClient
  (существующий, переиспользуется), NasaEpicTextureBuilder,
  EpicTextureFileCache, EpicPageSnapshotCache, GetEpicPageSnapshot,
  build_epic_router — в lifespan рядом с homepage-роутером.

presentation/web/templates/epic.html — полноэкранный canvas-mount,
  data-атрибуты centroid_lat/centroid_lon/texture_url, свой importmap
  (three + three/addons/), без hero/статистики/подписей.

presentation/web/static/css/epic.css — .epic-mount на весь viewport
  (position: fixed; inset: 0), канвас и fallback-картинка тем же inset.

presentation/web/static/js/epic-earth.js — сфера с кастомным
  ShaderMaterial (референс-ось из centroid, приближённая ортографическая
  проекция кадра на видимое полушарие, тёмная обратная сторона),
  OrbitControls (без pan, с damping, ограниченный зум), fallback при
  отсутствии WebGL.
```

## Тестирование

- `tests/infrastructure/test_nasa_clients.py` — фикстуры EPIC-провайдера
  дополняются `centroid_coordinates`; новые тесты на `fetch_day_frames`
  (парсинг `image` + `centroid_lat`/`centroid_lon`) и `fetch_frame_bytes`
  (URL по дате и имени кадра).
- `tests/infrastructure/test_epic_texture_builder.py` — первый `build()`
  качает и кеширует байты; второй `build()` той же даты не обращается к
  архиву повторно (только к метаданным); выбор среднего кадра на чётном
  и нечётном числе кадров; пустой список кадров → `None` без исключения.
- `tests/infrastructure/test_epic_texture_cache.py` — `get`/`set`/`exists`
  roundtrip и отклонение небезопасных ключей (по образцу
  `test_event_map_cache.py`).
- `tests/application/test_epic_page_query.py` — фейковые
  `EpicAvailability`/`EpicTextureBuilder`: пустой список дат → `None`;
  несколько дат → берётся `max`, не первая по порядку; `texture_builder`
  вернул `None` → итоговый снапшот `None`; успешный путь возвращает
  снапшот с ожидаемыми полями.
- `tests/presentation/test_epic_web_router.py` — `GET /epic` → 200 с
  data-атрибутами координат/текстуры при наличии снапшота, рендер
  `placeholder.html` при `None`; `GET /api/epic/textures/{key}.jpg` → 200
  + байты при наличии кеша, 404 при отсутствии. Названо не
  `test_epic_router.py` — этот файл уже занят тестом Telegram-роутера
  EPIC (`presentation/telegram/routers/epic_router.py`).

## Что реализовано

Полноэкранная страница `/epic`: 3D-глобус на `Three.js`, текстурированный
одним настоящим кадром EPIC за последнюю известную NASA дату,
сориентированным по `centroid_coordinates` этого кадра; свободное
вращение и зум через `OrbitControls`; обратное (непрофотографированное)
полушарие — сплошной тёмный цвет; фон и звёзды — уже существующие
общесайтовые (`starfield.js`, `tokens.css`); общий с ботом код скачивания
кадров EPIC вынесен в `infrastructure/nasa/epic_frames.py` вместо
дублирования.

## Что осознанно вне рамок

- Сшивка нескольких кадров в единую equirectangular-текстуру на весь шар
  (второй, более амбициозный вариант из обсуждения) — не делается сейчас;
  при желании — отдельное расширение поверх этой ТЗ.
- Подпись, дата кадра, координаты и любой текст поверх модели — не
  показываются на странице (прямой запрос «ничего лишнего»), хотя
  `frame_date` сохраняется в `EpicPageSnapshot` (нужен для ключа кэша).
- Точная картографическая репроекция диска EPIC на сферу (кривизна у
  края, атмосферные искажения) — шейдер использует приближённую
  ортографическую проекцию, не точную.
- Автовращение модели без участия пользователя — не реализуется
  (`OrbitControls.autoRotate` не включается).
- Живое обновление текстуры без перезагрузки страницы — не запрошено;
  страница показывает то, что было закешировано на момент захода/до
  истечения TTL.
