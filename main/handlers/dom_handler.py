import asyncio
import time
from typing import Dict, Optional
from venv import logger

from main.handlers.base_handler import BaseHandler


class DOMHandler(BaseHandler):
    def __init__(self, connection):
        super().__init__(connection)
        self._document_node_id = None
        self._enabled = False

    async def enable(self):
        if not self._enabled:
            await self.send_command("DOM.enable")
            self._enabled = True

    async def disable(self):
        """Отключение DOM-событий"""
        await self.send_command("DOM.disable")

    async def get_document(self, depth: int = -1, pierce: bool = False) -> Dict:
        """Получение документа"""
        response = await self.send_command("DOM.getDocument", {
            "depth": depth,
            "pierce": pierce
        })
        self._document_node_id = response["root"]["nodeId"]
        return response

    async def query_selector(self, selector: str, node_id: Optional[int] = None) -> Optional[int]:
        """Поиск элемента по селектору"""
        if node_id is None:
            if self._document_node_id is None:
                await self.get_document()
            node_id = self._document_node_id

        response = await self.send_command("DOM.querySelector", {
            "nodeId": node_id,
            "selector": selector
        })
        return response.get("nodeId")

    async def get_attributes(self, node_id: int) -> Dict[str, str]:
        """Получение атрибутов элемента"""
        response = await self.send_command("DOM.getAttributes", {
            "nodeId": node_id
        })
        return dict(zip(response["attributes"][::2], response["attributes"][1::2]))

    async def click(self, node_id: int, click_count: int = 1):
        """Клик по элементу"""
        box = await self.send_command("DOM.getBoxModel", {
            "nodeId": node_id
        })

        model = box["model"]
        x = (model["content"][0] + model["content"][2]) / 2
        y = (model["content"][1] + model["content"][5]) / 2

        await self.send_command("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": click_count
        })

        await self.send_command("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": click_count
        })