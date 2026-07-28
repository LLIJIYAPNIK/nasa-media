# TZ-weekly-highlights.md — еженедельный «зал славы»

## Цель

Реализовать пункт 10 текущего фокуса: в дополнение к ежедневной сводке (рутина,
проверяется на автомате) — редкий, но более драматичный контент раз в неделю:
самое заметное космическое событие недели, самый крупный (не ближайший —
см. «Решения») астероид недели, заметное событие на Земле. Реже — но за счёт
экстремальности каждого пункта интереснее пересылать, чем ежедневную рутину.

Предполагает, что `TZ-share-cards.md` уже реализован — итоги недели сразу
собираются как карточка-картинка, не текстовое сообщение с последующим
апгрейдом.

## Решения по неоднозначностям

- **Переиспользуем DONKI/NeoWs-клиенты через новый метод, не через новые
  классы.** `DonkiClient.fetch_for_day(day)` и `NeoWsClient.fetch_for_day(day)`
  (`infrastructure/nasa/donki_client.py`, `neows_client.py`) на самом деле
  разница только в диапазоне `startDate`/`endDate` (DONKI) и `start_date`/
  `end_date` (NeoWs) — оба API одинаково принимают произвольный диапазон дат
  за один запрос (проверено живыми запросами при написании
  `TZ-daily-digest.md` — DONKI отдавал неделю уведомлений одним вызовом).
  Добавляем `fetch_for_range(start: date, end: date)` на оба клиента,
  `fetch_for_day(day)` переписывается как `fetch_for_range(day, day)` — не
  дублирует HTTP-логику. Соответствующие Protocol'ы в
  `application/digest/ports.py` получают этот метод дополнительно к уже
  существующему.
- **EONET — тот же `fetch_recent()`, без изменений.** API не поддерживает
  диапазон дат вообще (см. `TZ-daily-digest.md`) — для еженедельных итогов
  используется тот же вызов с тем же лимитом, что и в ежедневном дайджесте;
  "заметное событие недели" здесь технически равно "самое свежее из последних
  открытых", как и в дайджесте — честно фиксирую, что настоящего
  ранжирования "по значимости за неделю" для Земли нет (единицы измерения
  магнитуды разные у разных категорий событий — акры для пожаров, узлы для
  штормов — несравнимы напрямую, см. «Вне рамок»).
- **Космическая погода — та же `pick_significant_space_weather`, только на
  недельном списке.** Приоритет типа (`GST > FLR > CME > IPS > RBE`) не
  меняется — просто на вход подаётся неделя уведомлений вместо одного дня.
  Новая функция не нужна.
- **Астероид недели — "самый крупный", не "самый близкий".** Новая функция
  `pick_largest_asteroid(asteroids) -> AsteroidHighlight | None` в
  `domain/digest/digest_text.py` (`max` по `diameter_max_m`) — рядом с уже
  существующей `pick_closest_asteroid`. Осознанное отличие от ежедневной
  сводки: близость больше подходит для "что происходит сегодня" (сближение
  может быть неопасным, но заметным по расстоянию), а недельные итоги — про
  "самое впечатляющее", и огромный далёкий астероид эффектнее маленького
  близкого.
- **Кеш — одна запись на неделю, ключ = дата понедельника этой недели.**
  Новая таблица `WeeklyHighlightModel(week_start_date unique, message_id
  unique)`, форма как у `DigestModel`. Новая чистая функция `week_start(day:
  date) -> date` в `domain/digest/week.py` (`day - timedelta(days=day.weekday())`)
  — понедельник как начало недели, ISO-стандарт.
- **`DeliverMediaForDate` переиспользуется без изменений — `day` в вызове
  означает "понедельник этой недели", не календарный день.** Тот же приём,
  что уже применялся для дайджеста (переиспользование общего use-case вместо
  нового): `DeliverMediaForDate.execute(week_start(date.today()), chat_id)`.
  `WeeklyHighlightsProvider.fetch(day)` трактует переданный `day` как начало
  недели и сам считает `end = day + timedelta(days=6)` внутри.
- **Замечен риск дублирования между `DigestSourceAdapter` и новым
  `WeeklyHighlightsSourceAdapter`.** Оба — дословно одна и та же реализация
  `MediaSourceAdapter` (`get_cached`/`fetch_and_cache`/`forward_cached`),
  отличающаяся только именем класса Entity (`DigestEntry` vs
  `WeeklyHighlightEntry`) и типом репозитория. Не схлопываю сейчас
  сознательно — как и с `EpicSourceAdapter`/`ApodSourceAdapter` в
  `TZ-gif-timelapse.md`, решается в обязательном рефакторинг-проходе после
  реализации этой фичи, когда третий одинаковый класс подряд делает
  дублирование неоспоримым, а не гипотетическим.
- **Расписание — по понедельникам, внутри уже существующего суточного
  цикла.** `periodic_broadcast` в `main.py` и так проверяет `date.today()`
  каждые 86400 секунд — добавляется условие `if today.weekday() == 0:` перед
  вызовом `broadcast_weekly_highlights.execute(week_start(today))`. Не
  заводим второй цикл/интервал ради одной еженедельной проверки — по той же
  причине, по которой в проекте нет `AsyncIOScheduler` (`TZ-core-transfer.md`).
- **Подписка — четвёртое значение `MediaSourceKind.WEEKLY_HIGHLIGHTS`.**
  Словарная реализация `User.is_subscribed`/`with_subscription` и
  `SqlAlchemyUserRepository.list_subscribed` (введена в `TZ-daily-digest.md`
  специально с расчётом на расширение) уже готова к четвёртому источнику без
  переписывания метода — только новая запись в словаре и колонка
  `weekly_highlights_subscribed` в `UserModel`.
- **UX — не новая кнопка в стартовом меню, а пункт внутри раздела "Сводка".**
  И дайджест, и итоги недели — один тематический раздел ("что происходит в
  космосе"), а не два независимых. `digest_kb.py` получает вторую пару кнопок:
  "Итоги недели" (`weekly_highlights_show`) + подписка/отписка на неё,
  `digest_router.py` — соответствующие хендлеры.

## Целевые файлы

```
domain/digest/week.py — week_start(day) -> date.

domain/digest/digest_text.py — pick_largest_asteroid(asteroids).

infrastructure/nasa/donki_client.py, neows_client.py — fetch_for_range(start, end);
  fetch_for_day становится тонкой обёрткой над ним.

application/digest/ports.py — fetch_for_range на SpaceWeatherClient/
  NearEarthObjectClient; WeeklyHighlightsRepository.get_by_date/save.

domain/digest/entities.py — WeeklyHighlightEntry(week_start_date, message_id).

application/digest/weekly_provider.py — WeeklyHighlightsProvider (реализует
  MediaProvider, по форме как DigestProvider, но с диапазоном дат и
  pick_largest_asteroid вместо pick_closest_asteroid), возвращает
  GeneratedImagePayload через card_builder.build_card(...).

application/digest/weekly_source_adapter.py — WeeklyHighlightsSourceAdapter
  (см. «Решения» про осознанное дублирование до рефакторинга).

infrastructure/db/models.py — WeeklyHighlightModel; UserModel.weekly_highlights_subscribed.

infrastructure/db/repositories.py — SqlAlchemyWeeklyHighlightsRepository;
  обновить словарь колонок в SqlAlchemyUserRepository.list_subscribed.

domain/users/entities.py — User.weekly_highlights_subscribed, запись в словаре
  полей подписки.

presentation/telegram/keyboards/digest_kb.py — кнопки "Итоги недели" +
  подписка/отписка.

presentation/telegram/routers/digest_router.py — weekly_highlights_show,
  register_subscribe_handlers(router, MediaSourceKind.WEEKLY_HIGHLIGHTS, ...).

presentation/telegram/subscribe_handler.py — _LABELS[WEEKLY_HIGHLIGHTS].

main.py — сборка WeeklyHighlightsProvider/адаптера/репозитория,
  broadcast_weekly_highlights, условие по дню недели в periodic_broadcast.
```

## Тестирование

- `tests/domain/test_week.py` — `week_start` на всех днях недели (в том
  числе на самом понедельнике — должен вернуть тот же день).
- `tests/domain/test_digest_text.py` — `pick_largest_asteroid` на списке из
  нескольких астероидов, пустом списке.
- `tests/infrastructure/test_nasa_clients.py` — `fetch_for_range` на
  многодневный ответ DONKI/NeoWs (форма ответа уже видна в тестах дайджеста —
  расширить диапазоном).
- `tests/application/test_weekly_highlights.py` — по образцу
  `test_digest_source_adapter.py` (кеш-хит/промах/публикация/пересылка) и
  отдельно тест на `WeeklyHighlightsProvider`, что он собирает лучший факт
  именно за диапазон недели, а не одного дня.
- `tests/presentation/test_digest_router.py` — расширить сценариями
  `weekly_highlights_show` и подпиской на `MediaSourceKind.WEEKLY_HIGHLIGHTS`.

## Что реализовано

Еженедельная (по понедельникам) сводка самого значимого космического
события, самого крупного астероида недели и заметного события на Земле —
как карточка-картинка, с собственной подпиской и кнопкой внутри раздела
"Сводка".

## Что осознанно вне рамок

- Настоящее ранжирование событий Земли "по значимости за неделю" — единицы
  измерения магнитуды несравнимы между категориями EONET, оставляем то же
  ограничение, что и в ежедневном дайджесте (см. «Решения»).
- Схлопывание `ApodSourceAdapter`/`DigestSourceAdapter`/
  `WeeklyHighlightsSourceAdapter` в один класс — фиксируется как явный
  кандидат для обязательного рефакторинг-прохода после этой фичи, не
  делается заранее.
- Настраиваемый день недели рассылки — фиксированный понедельник, не
  вынесено в конфигурацию.
