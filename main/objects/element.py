from typing import Optional, Dict, Any
from main.logging.logger import StepLogger  # обновлённый StepLogger


class Element:
    def __init__(self, node_id: int, backend_node_id: int, node_name: str,
                 box_model: Optional[Dict[str, Any]], document_url: Optional[str],
                 dom_handler=None, step_logger: Optional[StepLogger] = None):
        self.node_id = node_id
        self.backend_node_id = backend_node_id
        self.node_name = node_name
        self.box_model = box_model
        self.document_url = document_url
        self._dom_handler = dom_handler
        self._step_logger = step_logger

    def __repr__(self):
        return (f"<Element node_id={self.node_id}, backend_node_id={self.backend_node_id}, "
                f"node_name='{self.node_name}', url='{self.document_url}'>")

    async def click(self) -> bool:
        if self._step_logger:
            self._step_logger.log_step("Клик по элементу", True, str(self))
        if self._dom_handler:
            result = await self._dom_handler.click_element(self)
            if self._step_logger:
                self._step_logger.log_step("Результат клика", result)
            return result
        if self._step_logger:
            self._step_logger.log_step("Ошибка: DOMHandler не привязан", False)
        return False

    async def get_text(self) -> Optional[str]:
        if self._dom_handler:
            text = await self._dom_handler.get_text_by_element(self)
            if self._step_logger:
                self._step_logger.log_step("Получение текста", True, text or "")
            return text
        if self._step_logger:
            self._step_logger.log_step("Ошибка: DOMHandler не привязан при получении текста", False)
        return None

    async def get_attributes(self) -> Optional[Dict[str, str]]:
        if self._dom_handler:
            attrs = await self._dom_handler.get_attributes(self)
            if self._step_logger:
                self._step_logger.log_step("Получение атрибутов", True, str(attrs))
            return attrs
        if self._step_logger:
            self._step_logger.log_step("Ошибка: DOMHandler не привязан при получении атрибутов", False)
        return None

    async def scroll_into_view(self) -> bool:
        if self._dom_handler:
            result = await self._dom_handler.scroll_to_element(self)
            if self._step_logger:
                self._step_logger.log_step("Прокрутка к элементу", result)
            return result
        if self._step_logger:
            self._step_logger.log_step("Ошибка: DOMHandler не привязан при прокрутке", False)
        return False

    async def highlight(self, color="red", thickness="2px", duration=10.0):
        if self._dom_handler:
            result = await self._dom_handler.highlight_element_border(self.node_id, color, thickness, duration)
            if self._step_logger:
                self._step_logger.log_step("Подсветка элемента", result)
            return result
        if self._step_logger:
            self._step_logger.log_step("Ошибка: DOMHandler не привязан при подсветке", False)
        return False

    async def insert_text(self, text: str) -> bool:
        if self._dom_handler:
            result = await self._dom_handler.insert_text(self, text)
            if self._step_logger:
                self._step_logger.log_step("Ввод текста", result, text)
            return result
        if self._step_logger:
            self._step_logger.log_step("Ошибка: DOMHandler не привязан при вводе текста", False)
        return False

    async def move_mouse(self):
        if self._dom_handler:
            await self._dom_handler.move_mouse_on_element(self)
            await self._dom_handler.wait_for_page_dom_load()
            if self._step_logger:
                self._step_logger.log_step("Наведение курсора мыши", True)
        else:
            if self._step_logger:
                self._step_logger.log_step("Ошибка: DOMHandler не привязан при наведении курсора", False)
