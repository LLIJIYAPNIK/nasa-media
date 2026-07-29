# TZ-web-space-weather-detail.md — Полный список DONKI-событий в модалке «Космическая погода»

## Цель

Сейчас модалка карточки «Космическая погода» на главной странице веба
(`kind="space-weather"`) показывает только одно, заранее выбранное
«главное» событие DONKI за день (или фразу «Космос сегодня спокоен», если
подходящего события нет) — см. скриншот в обсуждении и код ниже. Выглядит
скучно и, что важнее, отбрасывает реальные данные: DONKI за день может
прислать несколько уведомлений разных типов, а пользователь видит максимум
одно. Задача — показать в модалке **все** уведомления DONKI за сегодня
списком, а под списком оставить короткий итог («Спокойно» / название самого
значимого типа события) — тот же принцип свёртки, что уже есть, но как вывод
после полного списка, а не вместо него.

Ограничено веб-модалкой карточки «Космическая погода» (`presentation/web`).
Telegram-сводка (`/digest`) не трогается — см. «Что осознанно вне рамок».

## Что уже есть

Данные уже приходят в приложение полным списком, без потери информации —
менять NASA-клиент не требуется:

- `DonkiClient.fetch_for_day` (`infrastructure/nasa/donki_client.py:23`) уже
  возвращает `Sequence[SpaceWeatherHighlight]` — **все** уведомления DONKI
  за день (`type=all` в запросе), не одно. Каждое —
  `SpaceWeatherHighlight(message_type: str, issued_at: datetime)` (сырой
  `messageBody` сознательно не парсится, см. `docs/tz/TZ-daily-digest.md`,
  раздел «Решения» — это ограничение не пересматривается этим ТЗ).
- Информация теряется на следующем шаге:
  `GetHomepageDetail._space_weather_detail` (`application/web/homepage_detail_query.py:132`)
  получает этот список и тут же схлопывает его в один элемент через
  `pick_significant_space_weather` (`domain/digest/digest_text.py:24`,
  приоритет `GST > FLR > CME > IPS > RBE`, `Report` и всё остальное
  игнорируется). Если совпадения по приоритету нет — `available=False`,
  `message="Космос сегодня спокоен."`, даже если DONKI прислал уведомления
  других типов (например, только `Report` или `SEP`).
- Подписи типов для веба — отдельный словарь `SPACE_WEATHER_TYPE_LABELS`
  (`application/web/homepage_query.py:14`, 5 типов: `GST/FLR/CME/IPS/RBE`),
  сознательно отдельный от `_SPACE_WEATHER_LABELS` в `domain/digest/digest_text.py`
  (тот — приватный, с эмодзи, заточен под Telegram-текст сводки).
- Модалка рендерится на клиенте: `GET /api/homepage/details/space-weather`
  отдаёт `dataclasses.asdict(HomepageDetail)`
  (`presentation/web/routers/homepage_router.py:66-72`), `modal.js`
  (`renderSpaceWeather`, строки 50-60) рисует `<dl>` с типом и временем
  одного события.

## Решения по неоднозначностям (с обоснованием)

- **Разделяем «есть ли вообще данные DONKI за день» и «есть ли значимое
  событие».** Сейчас оба вопроса отвечает один и тот же
  `pick_significant_space_weather is None`, из-за чего день с одним `Report`
  или `SEP` неотличим от дня без единого уведомления. Новое поведение:
  `available = bool(events)` (есть хоть одно уведомление любого типа) —
  список показывается; отдельно, независимо от `available`, вычисляется
  итоговая строка через уже существующий `pick_significant_space_weather`
  (пусто → «Спокойно», есть совпадение по приоритету → название типа).
  `available=False` (пустая модалка с фразой «Космос сегодня спокоен.», как
  сейчас) остаётся только для случая, когда DONKI не прислал вообще ничего —
  честно отражает реальный пустой ответ API, а не потерю данных.
- **Список — все типы без исключений, включая `Report` и любые типы вне
  текущей пятёрки (`SEP`, `MPC` — оба валидны для `type=all`, см. обсуждение
  DONKI API в чате).** «Все данные из API» в задаче — буквально все, не
  только «значимые» пять. `Report` по-прежнему не участвует в выборе
  итоговой строки (это еженедельный сводный документ, не событие дня, см.
  `TZ-daily-digest.md`), но в списке отображается наравне с остальными —
  иначе список выглядел бы обрезанным без объяснения.
- **`SPACE_WEATHER_TYPE_LABELS` расширяется до полного набора типов
  notifications-эндпоинта DONKI**: добавить `SEP` («Поток солнечных
  частиц»), `MPC` («Пересечение магнитопаузы»), `Report` («Еженедельный
  отчёт»). Правится только веб-словарь в `application/web/homepage_query.py`
  — `_SPACE_WEATHER_LABELS` в `domain/digest/digest_text.py` (Telegram) не
  трогается, т.к. Telegram-сводка вне рамок этого ТЗ (см. ниже). Для типа,
  которого нет и в расширенном словаре, — fallback на сырой `message_type`,
  как уже сделано в `SPACE_WEATHER_TYPE_LABELS.get(type, type)`.
- **Список сортируется по `issued_at` по возрастанию** (что произошло раньше
  — выше) — читается как хронология дня, а не как таблица без порядка.
- **`HomepageDetail` (`application/web/homepage_detail_query.py`) получает
  новое поле `space_weather_events: list[SpaceWeatherEventItem] | None`**,
  где `SpaceWeatherEventItem` — маленький `frozen`-датакласс
  `(type: str, label: str, issued_at: str)` в том же файле. Вложенный
  датакласс в списке `asdict()` сериализует рекурсивно без дополнительного
  кода в роутере — `presentation/web/routers/homepage_router.py` не
  меняется.
- **Существующие поля `space_weather_type` / `space_weather_label` /
  `space_weather_issued_at` переименовываются в `space_weather_summary_type`
  / `space_weather_summary_label` / `space_weather_summary_issued_at`.**
  Это уже не «единственное событие», а именно итоговая строка после списка
  — старое имя вводило бы в заблуждение при чтении JSON рядом с новым
  `space_weather_events`. `space_weather_summary_label` теперь заполняется
  всегда, когда `available=True` (значение `"Спокойно"`, если значимого
  события нет — так фраза для сводки не выдумывается на фронте, а приходит
  из API, как и остальной текст на странице); `space_weather_summary_type` /
  `space_weather_summary_issued_at` — `None` в этом случае (нет типа и
  времени у «спокойно»). Это точечный breaking change контракта
  `/api/homepage/details/space-weather`, но эндпоинт — внутренний для
  своего же фронтенда, внешних потребителей нет.
- **Заголовок модалки (`<h2>`) — статичный «Космическая погода», не название
  одного события.** Сейчас `renderSpaceWeather` берёт заголовком
  `detail.space_weather_label` — оправдано для одного события, но не для
  списка из нескольких разных типов. Совпадает с уже существующим паттерном
  статичных заголовков в `KIND_TITLES` (`modal.js:4-9`), используется как
  fallback и в `renderUnavailable`.
- **Оформление списка — простой `<ul>`, не `<dl>`** (`<dl>` в
  `modal.css:130-148` заточен под фиксированный набор пар «подпись —
  значение», как в карточке астероида; список переменной длины ему не
  соответствует). Итоговая строка — переиспользует класс
  `.detail-modal-notice` (акцентный цвет, уже есть в `modal.css:118-122`)
  или отдельный `.detail-modal-summary` с похожим оформлением — финальный
  выбор класса/отступов уточняется по живому скриншоту после первой сборки,
  по той же схеме, что и предыдущие раунды правок веба
  (`docs/tz/web-homepage-fixes*`), а не фиксируется здесь пиксель в пиксель.

## Целевые файлы

```
infrastructure/nasa/donki_client.py — без изменений (уже отдаёт полный список).

domain/digest/digest_text.py — без изменений (pick_significant_space_weather
  переиспользуется как есть, для итоговой строки).

application/web/homepage_query.py — SPACE_WEATHER_TYPE_LABELS: добавить SEP,
  MPC, Report.

application/web/homepage_detail_query.py —
  SpaceWeatherEventItem(type, label, issued_at) — новый датакласс;
  HomepageDetail: + space_weather_events: list[SpaceWeatherEventItem] | None,
  переименовать space_weather_type/label/issued_at →
  space_weather_summary_type/label/issued_at;
  _space_weather_detail: available = bool(events); строит events
  (сортировка по issued_at, label через SPACE_WEATHER_TYPE_LABELS) и summary
  (через pick_significant_space_weather, "Спокойно" по умолчанию).

presentation/web/static/js/modal.js — renderSpaceWeather: статичный h2,
  <ul> по detail.space_weather_events, итоговый <p> по
  detail.space_weather_summary_label (+ время, если summary_issued_at не null).

presentation/web/static/css/modal.css — стиль для нового списка событий
  (.detail-modal-event-list или аналог) и итоговой строки.
```

## Тестирование

- `tests/application/test_homepage_detail_query.py`:
  - переименовать/расширить `test_space_weather_detail_available_includes_type_and_time`
    под новые поля `space_weather_summary_*`;
  - новый тест: несколько событий разных типов за день → `available=True`,
    `space_weather_events` содержит все, отсортированы по `issued_at`;
  - новый тест: только `Report` (или только тип вне приоритетного списка) за
    день → `available=True` (список не пуст), но
    `space_weather_summary_label == "Спокойно"`, `space_weather_summary_type is None`;
  - `test_space_weather_detail_unavailable_when_calm` переименовать в
    `..._unavailable_when_no_events_at_all` и оставить только случай с
    полностью пустым списком от `FakeSpaceWeatherClient`.
- `tests/presentation/test_homepage_router.py` — обновить, если там
  зафиксированы старые имена полей `space_weather_*` в ожидаемом JSON.
- Ручная проверка (как и в предыдущих веб-раундах): скриншот модалки на дне
  с несколькими типами уведомлений и на «спокойном» дне.

## Что осознанно вне рамок

- **Telegram-сводка (`/digest`) не меняется** — она сознательно однострочная
  по каждому источнику (см. `TZ-daily-digest.md`, «UX»), и полный список
  DONKI-событий в мессенджере читался бы хуже, чем на веб-странице с
  прокруткой. Если понадобится позже — отдельное ТЗ.
- **Карточки «Астероид» и «Событие Земли» не трогаются.** У них нет
  естественного «итога» по типу спокойно/неспокойно — они и так показывают
  одно самое релевантное значение (ближайший астероид / самое свежее
  событие), это осмысленный дизайн, а не потеря данных, в отличие от
  космической погоды, где за день реально может быть несколько разнородных
  уведомлений.
- **Парсинг `messageBody`** (скорость CME, класс вспышки и т.п.) —
  сознательно не делается, решение зафиксировано в `TZ-daily-digest.md` и
  этим ТЗ не пересматривается.
- **Пагинация/сворачивание длинного списка**, если DONKI пришлёт аномально
  много уведомлений за день — не встречалось в живых проверках, отдельная
  доработка по факту, а не заранее.
