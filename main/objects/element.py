from typing import Optional, Dict, Any

from main.utils.math import get_center_coordinates

class Element:
    def __init__(self, node_id: int, backend_node_id: int, node_name: str,
                 box_model: Optional[Dict[str, Any]], document_url: Optional[str],
                 dom_handler=None, input_handler =None, logger = None):
        self.node_id = node_id
        self.backend_node_id = backend_node_id
        self.node_name = node_name
        self.box_model = box_model
        self.document_url = document_url
        self._dom_handler = dom_handler
        self._input_handler = input_handler
        self._log = logger

    async def click(self) -> bool:
        if self._dom_handler and self._input_handler:
            await self._input_handler.move_mouse_on_element(self)
            await self._input_handler.click_element(self)
            await self._dom_handler.wait_for_page_dom_load()

        return False

    async def get_text(self) -> Optional[str]:
        if self._input_handler:
            text = await self._input_handler.get_text_by_element(self)
            return text

        return None

    async def get_attributes(self) -> Optional[Dict[str, str]]:
        if self._dom_handler:
            attrs = await self._dom_handler.get_attributes(self)
            return attrs

        return None

    async def scroll_into_view(self) -> bool:
        if self._input_handler:
            result = await self._input_handler.scroll_to_element(self)
            return result
        else:
            return False

    async def highlight(self, color="red", thickness="2px", duration=10.0):
        if self._dom_handler:
            result = await self._dom_handler.highlight_element_border(self.node_id, color, thickness, duration)
            return result
        else:
            return False

    async def insert_text(self, text: str) -> bool:
        if self._input_handler:
            result = await self._input_handler.insert_text(self, text)
            await self._dom_handler.wait_for_page_dom_load()
            return result
        else:
            return False

    async def move_mouse(self):
        if self._dom_handler and self._input_handler:
            await self._input_handler.move_mouse_on_element(self)
            await self._dom_handler.wait_for_page_dom_load()

    async def focus(self) -> bool:
        """Навести фокус на элемент."""
        return await self._dom_handler.focus_on_element(self)

    async def clear(self) -> bool:
        """Очистить поле (Ctrl+A + Backspace)."""
        return await self._input_handler.clear_field(self)

    async def double_click(self) -> bool:
        """Двойной клик по элементу."""
        x, y = await get_center_coordinates(self.box_model)
        await self._input_handler.move_mouse(x, y)
        await self._input_handler.press_mouse(x, y)
        await self._input_handler.release_mouse(x, y)
        await self._input_handler.press_mouse(x, y)
        await self._input_handler.release_mouse(x, y)
        return True

    async def right_click(self) -> bool:
        """Клик правой кнопкой."""
        x, y = await get_center_coordinates(self.box_model)
        await self._input_handler.move_mouse(x, y)
        await self._input_handler.press_mouse(x,y,1)
        await self._input_handler.release_mouse(x,y,1)
        return True