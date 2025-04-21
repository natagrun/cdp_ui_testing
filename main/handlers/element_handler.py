import asyncio
import json
from typing import Optional, Dict, List, Union
import logging

from main.handlers.base_handler import BaseHandler
from main.handlers.dom_handler import DOMHandler

logger = logging.getLogger(__name__)

import json
from typing import Optional, Dict, Union
import logging

logger = logging.getLogger(__name__)


async def _parse_cdp_response(response: Union[str, Dict]) -> Dict:
    """Парсит ответ CDP (может быть строкой JSON или уже словарём)."""
    if isinstance(response, str):
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse CDP response: {response}")
            return {}
    return response


class ElementHandler(BaseHandler):
    """Обработчик для взаимодействия с элементами DOM."""

    def __init__(self, dom_handler: DOMHandler):
        super().__init__(dom_handler.client)
        self.dom = dom_handler

    async def click(
            self,
            node_id: int,
            click_count: int = 1,
            delay: float = 0,
            button: str = "left"
    ) -> bool:
        """Клик по элементу.

        Args:
            node_id: ID узла.
            click_count: Количество кликов.
            delay: Задержка между нажатием и отпусканием (в мс).
            button: Кнопка мыши ("left", "right", "middle").

        Returns:
            True, если клик выполнен успешно.
        """
        try:
            # Получаем координаты элемента
            box_response = await self.dom.get_box_model(node_id)
            box_data = await _parse_cdp_response(box_response)

            if not box_data or "model" not in box_data.get("result", {}):
                logger.error("Box model not found or invalid")
                return False

            box_model = box_data["result"]["model"]

            # Берем центр элемента
            content = box_model.get("content", [])
            if len(content) < 6:
                logger.error("Invalid box model content")
                return False

            x = (content[0] + content[2]) / 2
            y = (content[1] + content[5]) / 2

            # Нажимаем кнопку мыши
            await self.send_request("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": button,
                "clickCount": click_count
            })

            if delay > 0:
                await asyncio.sleep(delay / 1000)

            # Отпускаем кнопку мыши
            await self.send_request("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": button,
                "clickCount": click_count
            })
            return True
        except Exception as e:
            logger.error(f"Click error: {e}")
            return False

    # Остальные методы остаются без изменений (type_text, get_text и т.д.)
    async def type_text(
            self,
            node_id: int,
            text: str,
            delay: float = 0
    ) -> bool:
        """Ввод текста в элемент.

        Args:
            node_id: ID узла.
            text: Текст для ввода.
            delay: Задержка между символами (в мс).

        Returns:
            True, если текст введен успешно.
        """
        try:
            # Фокусируемся на элементе
            await self.send_request("DOM.focus", {"nodeId": node_id})

            for char in text:
                await self.send_request("Input.insertText", {"text": char})
                if delay > 0:
                    await asyncio.sleep(delay / 1000)
            return True
        except Exception as e:
            logger.error(f"Type text error: {e}")
            return False

    async def get_text(self, node_id: int) -> Optional[str]:
        """Получить текст элемента.

        Args:
            node_id: ID узла.

        Returns:
            Текст элемента или None.
        """
        try:
            response = await self.send_request("DOM.getOuterHTML", {"nodeId": node_id})
            html = response.get("result", {}).get("outerHTML", "")

            # Простейшая реализация - можно заменить на более точный парсинг
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator=" ", strip=True)
        except Exception as e:
            logger.error(f"Get text error: {e}")
            return None

    async def get_property(
            self,
            node_id: int,
            property_name: str
    ) -> Optional[Union[str, bool, int, float]]:
        """Получить значение свойства элемента.

        Args:
            node_id: ID узла.
            property_name: Имя свойства.

        Returns:
            Значение свойства или None.
        """
        attrs = await self.dom.get_attributes(node_id)
        return attrs.get(property_name)

    async def is_visible(self, node_id: int) -> bool:
        """Проверить, видим ли элемент.

        Args:
            node_id: ID узла.

        Returns:
            True, если элемент видим.
        """
        try:
            box_model = await self.dom.get_box_model(node_id)
            if not box_model:
                return False

            # Проверяем, что элемент имеет площадь
            width = box_model["content"][2] - box_model["content"][0]
            height = box_model["content"][5] - box_model["content"][1]
            return width > 0 and height > 0
        except Exception as e:
            logger.error(f"Visibility check error: {e}")
            return False
