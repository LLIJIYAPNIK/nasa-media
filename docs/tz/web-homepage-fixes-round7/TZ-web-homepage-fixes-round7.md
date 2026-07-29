# TZ-web-homepage-fixes-round7.md — седьмой раунд доработки главной страницы

## Контекст

Rounds 5–6 (`docs/tz/web-homepage-fixes-round5/`,
`docs/tz/web-homepage-fixes-round6/`) слиты в `main` (#24). При живой
проверке карточки «Картинка дня» — NASA APOD иногда ещё не опубликован на
текущую дату (ручная модерация/часовые пояса публикации, либо `media_type`
за сегодня — видео, а не картинка: `ApodClient.fetch_raw`,
`infrastructure/nasa/apod_client.py`, тоже считает это «недоступно»).
Модалка в этом случае показывала только текст «Картинка дня на сегодня ещё
не опубликована NASA» без единого визуального элемента.

## Решение

`GetHomepageDetail._apod_detail` (`application/web/homepage_detail_query.py`)
при `MediaNotAvailable` за сегодня не сразу отдаёт `available=False`, а
пробует `today - timedelta(days=1)`. Если вчерашний APOD доступен —
возвращается `available=True` с уже вчерашними данными плюс `message` с
пояснением, что это вчерашняя картинка. Если недоступен и вчерашний день
(маловероятно, но возможно) — отдаётся прежнее поведение, пустая модалка с
текстом.

Однократный фолбэк, не рекурсивный поиск вглубь дней — если NASA не
опубликовала два дня подряд, дальнейшие попытки не добавляют пользы
относительно понятного сообщения об отсутствии данных.

`presentation/web/static/js/modal.js`: `renderApod` получил необязательный
блок `.detail-modal-notice` — рендерится только когда `detail.message`
присутствует (то есть только в сценарии фолбэка; обычный успешный APOD
`message` не выставляет). `modal.css` — стиль под акцентный цвет
(`--color-accent-soft`), меньше основного текста, чтобы читаться как
пояснение, а не как часть описания картинки.

## Целевые файлы

```
application/web/homepage_detail_query.py — _apod_detail_fallback_to_previous_day.
presentation/web/static/js/modal.js — renderApod: notice-блок.
presentation/web/static/css/modal.css — .detail-modal-notice.
tests/application/fakes.py — FakeApodRawClient.unavailable_days.
tests/application/test_homepage_detail_query.py — тесты на фолбэк и на
  отсутствие данных за оба дня.
```

## Тестирование

Юнит-тесты (`uv run pytest`, `uv run mypy .`, `uv run ruff check .`) —
зелёные. Живая проверка через `uv run python -m presentation.web`:
`/api/homepage/details/apod` на дату, где сегодняшний APOD — видео
(`media_type: video`), вернул вчерашний (`media_type: image`) с `message`
про фолбэк вместо пустой модалки.

## Что осознанно вне рамок

- Фолбэк ограничен одним днём назад, не пробует более ранние даты.
