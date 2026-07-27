from __future__ import annotations

import asyncio

from googletrans import Translator as _GoogleTranslator


class GoogleRuTranslator:
    """Обёртка над googletrans — поведение и стабильность не трогаем (вне
    скоупа), только прячем библиотеку за портом Translator и уводим её
    синхронный HTTP-вызов в поток, чтобы не блокировать event loop бота.
    """

    def __init__(self) -> None:
        self._translator = _GoogleTranslator()

    async def translate_to_ru(self, text: str) -> str:
        result = await asyncio.to_thread(self._translator.translate, text, dest="ru")
        return result.text
