import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class Element:
    def __init__(self, node_id: int, backend_node_id: int, node_name: str,
                 box_model: Optional[Dict[str, Any]], document_url: Optional[str],
                 dom_handler=None):
        self.node_id = node_id
        self.backend_node_id = backend_node_id
        self.node_name = node_name
        self.box_model = box_model
        self.document_url = document_url
        self._dom_handler = dom_handler  # ссылка на DOMHandler

    def __repr__(self):
        return (f"<Element node_id={self.node_id}, backend_node_id={self.backend_node_id}, "
                f"node_name='{self.node_name}', url='{self.document_url}'>")

    def bind_handler(self, handler):
        """Привязать DOMHandler после создания (если ещё не привязан)."""
        self._dom_handler = handler

    async def click(self) -> bool:
        if self._dom_handler:
            return await self._dom_handler.click_element(self)
        logger.error("DOMHandler is not attached to Element")
        return False

    async def get_text(self) -> Optional[str]:
        if self._dom_handler:
            return await self._dom_handler.get_text_by_element(self)
        logger.error("DOMHandler is not attached to Element")
        return None

    async def get_attributes(self) -> Optional[Dict[str, str]]:
        if self._dom_handler:
            return await self._dom_handler.get_attributes(self)
        logger.error("DOMHandler is not attached to Element")
        return None

    async def scroll_into_view(self) -> bool:
        if self._dom_handler:
            return await self._dom_handler.scroll_to_element(self)
        logger.error("DOMHandler is not attached to Element")
        return False

    async def highlight(self, color="red", thickness="2px", duration=10.0):
        if self._dom_handler:
            return await self._dom_handler.highlight_element_border(self.node_id, color, thickness, duration)
        logger.error("DOMHandler is not attached to Element")
        return False

    async def insert_text(self, text: str) -> bool:
        if self._dom_handler:
            return await self._dom_handler.insert_text(self, text)
        logger.error("DOMHandler is not attached to Element")
        return False

    async def move_mouse(self):
        if self._dom_handler:
            await self._dom_handler.move_mouse_on_element(self)
            await self._dom_handler.wait_for_page_dom_load()