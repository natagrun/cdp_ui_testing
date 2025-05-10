from typing import Optional

from main.handlers.dom_handler import DOMHandler
from main.handlers.navigation_handler import NavigationHandler
from main.handlers.page_handler import PageHandler
from main.objects.element import Element


class Assertions:
    """
    Набор вспомогательных assert-функций для проверки DOM-состояний и взаимодействий.
    Используется при тестировании и отладке.
    """

    def __init__(self, logger):
        self.log = logger.getChild("Assertions")

    def assert_element_exists(self, element: Optional[Element], message: str = "Element not found"):
        assert element is not None, message
        self.log.info("Проверка assert_element_exists пройдена")

    def assert_text_equals(self, actual: Optional[str], expected: str, message: Optional[str] = None):
        assert actual == expected, message or f"Expected '{expected}', got '{actual}'"
        self.log.info(f"Проверка assert_text_equals пройдена: {actual} == {expected}")

    async def assert_visible(self, dom: DOMHandler, node_id: int):
        visible = await dom.is_element_visible(node_id)
        assert visible, f"Element {node_id} is not visible"
        self.log.info(f"Проверка assert_visible пройдена для node_id={node_id}")

    async def assert_clickable(self, dom: DOMHandler, node_id: int):
        clickable = await dom.is_element_clickable(node_id)
        assert clickable, f"Element {node_id} is not clickable"
        self.log.info(f"Проверка assert_clickable пройдена для node_id={node_id}")

    async def assert_text_contains(self, dom: DOMHandler, element: Element, substring: str):
        text = await dom.get_text_by_element(element)
        assert substring in text, f"Expected '{substring}' in text, got '{text}'"
        self.log.info(f"Проверка assert_text_contains пройдена: найдено '{substring}' в '{text}'")

    async def assert_attribute_equals(self, dom: DOMHandler, element: Element, attr: str, expected_value: str):
        attrs = await dom.get_attributes(element)
        actual = attrs.get(attr) if attrs else None
        assert actual == expected_value, f"Expected attribute '{attr}' = '{expected_value}', got '{actual}'"
        self.log.info(f"Проверка assert_attribute_equals пройдена: {attr} == {expected_value}")

    async def assert_navigation_history_exists(self, navigation: NavigationHandler):
        history = await navigation.get_navigation_history()
        assert history and len(history) > 0, "Navigation history is empty or not found"
        self.log.info("Проверка assert_navigation_history_exists пройдена")

    async def assert_can_navigate_back(self, navigation: NavigationHandler):
        history = await navigation.get_navigation_history()
        assert navigation.current_index is not None and navigation.current_index > 0, "Cannot navigate back"
        self.log.info("Проверка assert_can_navigate_back пройдена")

    async def assert_url_contains(self, navigation: NavigationHandler, substring: str):
        url = await navigation.get_current_url()
        assert substring in url, f"Expected URL to contain '{substring}', got '{url}'"
        self.log.info(f"Проверка assert_url_contains пройдена: найдено '{substring}' в '{url}'")

    async def assert_page_loaded_within(self, page: PageHandler, timeout: float = 5.0):
        result = await page.wait_for_page_dom_load(timeout=timeout)
        assert result["status"] == "completed", f"Page did not load properly: {result}"
        self.log.info("Проверка assert_page_loaded_within пройдена")

    async def assert_element_text_equals(self, dom: DOMHandler, element: Element, expected_text: str):
        """
        Проверяет, что текст элемента точно равен expected_text.
        """
        text = await dom.get_text_by_element(element)
        assert text == expected_text, f"Ожидался текст '{expected_text}', получено '{text}'"
        self.log.info(f"assert_element_text_equals пройдено: '{text}' == '{expected_text}'")

    async def assert_element_text_contains(self, dom: DOMHandler, element: Element, substring: str):
        """
        Проверяет, что текст элемента содержит указанную подстроку.
        """
        text = await dom.get_text_by_element(element)
        assert substring in text, f"Ожидалось наличие '{substring}' в тексте, но получено '{text}'"
        self.log.info(f"assert_element_text_contains пройдено: '{substring}' in '{text}'")
