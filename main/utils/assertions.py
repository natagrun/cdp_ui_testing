import asyncio
from typing import Optional

from main.handlers import *
from main.handlers.dom_handler import DOMHandler
from main.handlers.navigation_handler import NavigationHandler
from main.handlers.page_handler import PageHandler
from main.objects.element import Element


class Assertions:
    """
    Набор вспомогательных assert-функций для проверки DOM-состояний и взаимодействий.
    Используется при тестировании и отладке.
    """

    @staticmethod
    def assert_element_exists(element: Optional[Element], message: str = "Element not found"):
        assert element is not None, message

    @staticmethod
    def assert_text_equals(actual: Optional[str], expected: str, message: Optional[str] = None):
        assert actual == expected, message or f"Expected '{expected}', got '{actual}'"

    @staticmethod
    async def assert_visible(dom: DOMHandler, node_id: int):
        visible = await dom.is_element_visible(node_id)
        assert visible, f"Element {node_id} is not visible"

    @staticmethod
    async def assert_clickable(dom: DOMHandler, node_id: int):
        clickable = await dom.is_element_clickable(node_id)
        assert clickable, f"Element {node_id} is not clickable"

    @staticmethod
    async def assert_text_contains(dom: DOMHandler, element: Element, substring: str):
        text = await dom.get_text_by_element(element)
        assert substring in text, f"Expected '{substring}' in text, got '{text}'"

    @staticmethod
    async def assert_attribute_equals(dom: DOMHandler, element: Element, attr: str, expected_value: str):
        attrs = await dom.get_attributes(element)
        actual = attrs.get(attr) if attrs else None
        assert actual == expected_value, f"Expected attribute '{attr}' = '{expected_value}', got '{actual}'"

    @staticmethod
    async def assert_navigation_history_exists(navigation: NavigationHandler):
        history = await navigation.get_navigation_history()
        assert history is not None and len(history) > 0, "Navigation history is empty or not found"

    @staticmethod
    async def assert_can_navigate_back(navigation: NavigationHandler):
        history = await navigation.get_navigation_history()
        assert navigation.current_index is not None and navigation.current_index > 0, "Cannot navigate back"

    @staticmethod
    async def assert_url_contains(navigation: NavigationHandler, substring: str):
        url = await navigation.get_current_url()
        assert substring in url, f"Expected URL to contain '{substring}', got '{url}'"

    @staticmethod
    async def assert_page_loaded_within(page: PageHandler, timeout: float = 5.0):
        result = await page.wait_for_page_dom_load(timeout=timeout)
        assert result["status"] == "completed", f"Page did not load properly: {result}"