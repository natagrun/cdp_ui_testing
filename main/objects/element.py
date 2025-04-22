import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class Element:
    def __init__(self, node_id: int, backend_node_id: int, node_name: str,
                 box_model: Optional[Dict[str, Any]], document_url: Optional[str],
                 dom_handler=None, step_logger=None):
        self.node_id = node_id
        self.backend_node_id = backend_node_id
        self.node_name = node_name
        self.box_model = box_model
        self.document_url = document_url
        self._dom_handler = dom_handler  # ссылка на DOMHandler
        self._step_logger = step_logger  # логгер шагов (опционально)

    def __repr__(self):
        return (f"<Element node_id={self.node_id}, backend_node_id={self.backend_node_id}, "
                f"node_name='{self.node_name}', url='{self.document_url}'>")

    async def click(self) -> bool:
        logger.info(f"Clicking element: {self}")
        if self._step_logger:
            self._step_logger.log_step("Клик по элементу", True, str(self))
        if self._dom_handler:
            result = await self._dom_handler.click_element(self)
            if self._step_logger:
                self._step_logger.log_step("Результат клика", result)
            logger.info(f"Click result: {result}")
            return result
        logger.error("DOMHandler is not attached to Element")
        if self._step_logger:
            self._step_logger.log_step("Ошибка DOMHandler при клике", False)
        return False

    async def get_text(self) -> Optional[str]:
        logger.info(f"Getting text from element: {self}")
        if self._dom_handler:
            text = await self._dom_handler.get_text_by_element(self)
            logger.debug(f"Text received: {text}")
            if self._step_logger:
                self._step_logger.log_step("Получение текста", True, f"Text: {text}")
            return text
        logger.error("DOMHandler is not attached to Element")
        if self._step_logger:
            self._step_logger.log_step("Ошибка DOMHandler при получении текста", False)
        return None

    async def get_attributes(self) -> Optional[Dict[str, str]]:
        logger.info(f"Getting attributes from element: {self}")
        if self._dom_handler:
            attrs = await self._dom_handler.get_attributes(self)
            logger.debug(f"Attributes received: {attrs}")
            if self._step_logger:
                self._step_logger.log_step("Получение атрибутов", True, str(attrs))
            return attrs
        logger.error("DOMHandler is not attached to Element")
        if self._step_logger:
            self._step_logger.log_step("Ошибка DOMHandler при получении атрибутов", False)
        return None

    async def scroll_into_view(self) -> bool:
        logger.info(f"Scrolling element into view: {self}")
        if self._dom_handler:
            result = await self._dom_handler.scroll_to_element(self)
            logger.info(f"Scroll result: {result}")
            if self._step_logger:
                self._step_logger.log_step("Прокрутка к элементу", result)
            return result
        logger.error("DOMHandler is not attached to Element")
        if self._step_logger:
            self._step_logger.log_step("Ошибка DOMHandler при прокрутке", False)
        return False

    async def highlight(self, color="red", thickness="2px", duration=10.0):
        logger.info(f"Highlighting element: {self} with color={color}, thickness={thickness}, duration={duration}")
        if self._dom_handler:
            result = await self._dom_handler.highlight_element_border(self.node_id, color, thickness, duration)
            logger.info(f"Highlight result: {result}")
            if self._step_logger:
                self._step_logger.log_step("Подсветка элемента", result)
            return result
        logger.error("DOMHandler is not attached to Element")
        if self._step_logger:
            self._step_logger.log_step("Ошибка DOMHandler при подсветке", False)
        return False

    async def insert_text(self, text: str) -> bool:
        logger.info(f"Inserting text into element: {self}, text='{text}'")
        if self._dom_handler:
            result = await self._dom_handler.insert_text(self, text)
            logger.info(f"Insert text result: {result}")
            if self._step_logger:
                self._step_logger.log_step("Ввод текста", result, text)
            return result
        logger.error("DOMHandler is not attached to Element")
        if self._step_logger:
            self._step_logger.log_step("Ошибка DOMHandler при вводе текста", False)
        return False

    async def move_mouse(self):
        logger.info(f"Moving mouse to element: {self}")
        if self._dom_handler:
            await self._dom_handler.move_mouse_on_element(self)
            await self._dom_handler.wait_for_page_dom_load()
            if self._step_logger:
                self._step_logger.log_step("Наведение курсора мыши", True)
            logger.debug("Mouse moved on element and DOM load awaited")
        else:
            logger.error("DOMHandler is not attached to Element")
            if self._step_logger:
                self._step_logger.log_step("Ошибка DOMHandler при наведении курсора", False)
