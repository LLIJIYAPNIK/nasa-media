# TZ-share-cards.md — карточки-картинки для шаринга

## Цель

Реализовать пункт 9 текущего фокуса: сегодня сводка и факты дня рождения —
текстовые сообщения. Текст из Telegram неудобно репостить в чужой чат/сторис
(нужно пересылать сообщение целиком, со ссылкой на бота), а картинку — один
тап "поделиться". Генерируем изображение-карточку вместо текста для дайджеста
и для космических фактов дня рождения (`TZ-birthday-cosmic-facts.md` —
предполагается уже реализованным до этого пункта, если следуете
рекомендованному порядку).

## Решения по неоднозначностям

- **Pillow, без новых зависимостей.** В проекте уже `pillow>=12.3.0`
  (используется для GIF EPIC и ресайза одиночных фото). Начиная с Pillow
  10.1, `ImageFont.load_default(size=N)` отдаёт масштабируемый растровый шрифт
  — не требуется подключать/лицензировать сторонний `.ttf`-файл в
  публичном репозитории. Раньше это было бы проблемой (старый
  `load_default()` без параметра — крошечный нечитаемый шрифт), сейчас — нет.
- **Формат карточки — 1080×1080, PNG.** Квадрат — универсальный формат под
  Telegram/Stories/большинство соцсетей без обрезки. PNG, не JPEG — текст на
  сплошном фоне сжимается без артефактов, в отличие от JPEG.
- **Без переноса строк по ширине (word wrap) — вызывающий код обязан
  передавать уже короткие строки.** Реализация автоматического переноса с
  учётом ширины шрифта — отдельная, не короткая задача (нужно мерить ширину
  текста через `draw.textlength` и разбивать по словам). И `build_digest_text`
  (точнее, новый `build_digest_lines`, см. ниже), и `build_cosmic_facts_text`
  уже устроены как короткие, самостоятельные строки-факты — ограничение не
  создаёт проблему на практике, а не только "пока не создаёт".
- **Новый пейлоад — `GeneratedImagePayload(image_bytes: bytes, caption: str
  | None = None)`**, добавляется в объединение `MediaPayload`
  (`application/media/ports.py`) рядом с `SinglePhotoPayload`/
  `AnimationPayload`/`TextPayload`. `TelegramAdminChatGateway.publish()`
  получает ветку `_publish_generated_image` — `temp_file(payload.image_bytes,
  ".png")` (уже существующий контекст-менеджер из `infrastructure/files/
  temp_file.py`) → `bot.send_photo(FSInputFile(...), caption=payload.caption)`.
- **Дайджест: `DigestProvider.fetch()` возвращает `GeneratedImagePayload`
  вместо `TextPayload`.** `digest_text.py` разбивается на
  `build_digest_lines(...) -> list[str]` (возвращает строки по отдельности —
  заголовок и три факта) и `build_digest_text(...)`, которая теперь просто
  `"\n".join(build_digest_lines(...))` — переиспользует ту же логику выбора
  фактов, не дублирует её. `DigestProvider` вызывает `build_digest_lines(...)`,
  передаёт в `card_builder.build_card(title=..., lines=...)`, использует
  короткий текст (например, первую строку — заголовок с датой) как `caption`
  сгенерированной картинки.
- **Факты дня рождения: аналогично, но не через admin-чат.** Факты
  персональные (свои у каждого пользователя), поэтому не кешируются и не
  идут через `AdminChatGateway` — как и сейчас, отправляются напрямую. Нужен
  новый метод на `GreetingSender` (`application/media/ports.py`):
  `send_image(chat_id: int, image_bytes: bytes, caption: str | None) -> None`.
  Не заводим отдельный порт ради одного метода — `GreetingSender` уже
  концептуально "личное сообщение в обход admin-чата", `send_image` — тот же
  смысл, другой тип контента. `TelegramGreetingSender.send_image` — тот же
  паттерн `temp_file` + `bot.send_photo`.
- **`presentation/telegram/routers/apod_router.py` и
  `application/users/send_birthday_greetings.py` меняют `send_text(...)` на
  `send_image(card_bytes, caption=...)`** для космических фактов — сама точка
  вызова не меняется, меняется что именно отправляется.
- **`TextPayload` (введён в `TZ-daily-digest.md` специально под дайджест)
  после этой фичи остаётся без единого потребителя** — дайджест переходит на
  `GeneratedImagePayload`, больше его никто не использует. Не оставляем как
  мёртвый вес "на будущее": убираем `TextPayload` из `MediaPayload` и ветку
  `_publish_text` из `TelegramAdminChatGateway` в рамках этой же фичи (тот же
  принцип, что и с `PhotoGroupPayload`/`_publish_group` при переходе EPIC на
  GIF в `TZ-gif-timelapse.md`). Если к моменту реализации у `TextPayload`
  появится другой потребитель — сохранить и отметить это здесь, не убирать
  вслепую по этому ТЗ.
- **Оформление карточки — минимальное, не тема/брендинг бота.** Один тёмный
  фон (например, `(10, 14, 30)` — глубокий тёмно-синий, не чёрный), один цвет
  текста, без логотипа/декоративных элементов. Это сознательно facts-first
  дизайн, не попытка сделать "фирменный стиль" — при желании можно доработать
  визуально позже отдельной фичей, не смешивая с этой.

## Целевые файлы

```
infrastructure/files/card_builder.py — build_card(title: str, lines: Sequence[str])
  -> bytes (PNG), блокирующая Pillow-отрисовка в потоке (asyncio.to_thread,
  тот же приём, что gif_builder.py/temp_file.py).

application/media/ports.py — GeneratedImagePayload в MediaPayload;
  GreetingSender.send_image(...).

infrastructure/telegram/admin_chat_gateway.py — ветка _publish_generated_image.

infrastructure/telegram/greeting_sender.py — TelegramGreetingSender.send_image.

domain/digest/digest_text.py — build_digest_lines(...) выделяется из
  build_digest_text(...), последняя становится тонкой обёрткой.

application/digest/provider.py — DigestProvider.fetch() возвращает
  GeneratedImagePayload вместо TextPayload.

domain/users/cosmic_facts.py — аналогичное разделение build_cosmic_facts_lines/
  build_cosmic_facts_text, если ещё не сделано в TZ-birthday-cosmic-facts.md.

presentation/telegram/routers/apod_router.py,
application/users/send_birthday_greetings.py — send_text → send_image для
  космических фактов дня рождения.
```

## Тестирование

- `tests/infrastructure/test_card_builder.py` — по образцу
  `test_gif_builder.py`: собрать карточку из тестовых строк, прочитать
  обратно через `Image.open`, проверить формат (`PNG`) и размеры (1080×1080).
- `tests/domain/test_digest_text.py` — `build_digest_lines` возвращает
  ожидаемый список строк на всех уже существующих сценариях (пусто/есть по
  каждому источнику); `build_digest_text` даёт тот же результат, что и раньше
  (регрессия — join тех же строк).
- `tests/application/test_digest_source_adapter.py`/фейки — обновить под
  `GeneratedImagePayload` вместо `TextPayload` в `fetch_and_cache`.
- `tests/infrastructure/test_admin_chat_gateway.py` — новый тест
  `_publish_generated_image` по образцу `_publish_single`/`_publish_animation`.
- `tests/presentation/test_apod_birthday.py` — обновить проверку отправки
  фактов дня рождения на `send_image` вместо `send_text` (сигнатура мока
  меняется).

## Что реализовано

Дайджест и факты дня рождения отправляются как изображение-карточка вместо
текстового сообщения — с общей инфраструктурой генерации (`card_builder.py`),
новым вариантом пейлоада в общем механизме кеширования и новым методом
персональной отправки в обход кеша.

## Что осознанно вне рамок

- Автоматический перенос длинного текста по ширине — не реализуется (см.
  «Решения»), ответственность на вызывающем коде передавать короткие строки.
- Визуальный брендинг карточки (логотип, акцентные цвета, иллюстрации) — не
  запрошено, дизайн facts-first и минимальный.
- Карточки для APOD/EPIC (уже фото/анимация сами по себе) — не нужны, эта
  фича только про изначально текстовый контент.
- Итоги недели (`TZ-weekly-highlights.md`) сразу используют карточки — не
  апгрейд задним числом, а часть той фичи, если реализуется после этой.
