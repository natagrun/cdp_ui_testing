import json
import logging
from typing import Optional, Dict, Union, Tuple, Any

from new_main.handlers.base_handler import BaseHandler
from new_main.handlers.page_handler import PageHandler

logger = logging.getLogger(__name__)


async def _parse_response(response: Union[str, Dict]) -> Dict:
    """Парсит ответ CDP (может быть строкой JSON или уже словарём)."""
    if isinstance(response, str):
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CDP response: {e}")
            return {}
    return response


async def get_center_coordinates(model):
    if not model:
        logger.error("No box model data")
        return False

    # Координаты центра элемента
    x = (model["content"][0] + model["content"][2]) / 2
    y = (model["content"][1] + model["content"][5]) / 2

    return x, y


class DOMHandler(BaseHandler):
    """Обработчик для работы с DOM через Chrome DevTools Protocol."""

    async def enable_dom(self) -> Dict:
        """Активировать протокол DOM."""
        response = await self.send_request("DOM.enable")
        parsed = await _parse_response(response)
        logger.debug(f"DOM enabled: {parsed}")
        return parsed

    async def disable_dom(self) -> Dict:
        """Деактивировать протокол DOM."""
        response = await self.send_request("DOM.disable")
        parsed = await _parse_response(response)
        logger.debug(f"DOM disabled: {parsed}")
        return parsed

    async def get_document(self, depth: int = 2) -> Dict:
        """Получить корневой элемент документа."""
        response = await self.send_request("DOM.getDocument", {"depth": depth})
        parsed = await _parse_response(response)
        logger.debug(f"Document retrieved: {parsed}")
        return parsed

    async def query_selector(self, root_node_id: int, selector: str) -> Optional[int]:
        query_response = await self.send_request("DOM.querySelector", {
            "nodeId": root_node_id,
            "selector": selector
        })
        parsed_query = await _parse_response(query_response)

        while parsed_query.get("result", {}).get("nodeId") is None:
            query_response = await self.client.receive_message()
            parsed_query = await _parse_response(query_response)
            if parsed_query.get("result", {}).get("nodeId") is not None:
                break

        node_id = parsed_query.get("result", {}).get("nodeId")
        if not node_id:
            logger.error(f"Element with selector '{selector}' not found")
            return None
        return node_id

    async def perform_search(self, xpath: str):
        """Найти первый элемент по XPath."""
        result_count = 0
        search_id = ""
        try:
            params = {
                "query": xpath,
                "includeUserAgentShadowDOM": True
            }

            search_response = await self.send_request("DOM.performSearch", params)
            parsed_search = await _parse_response(search_response)

            search_id = parsed_search.get("searchId") or parsed_search.get("result", {}).get("searchId")
            logger.error(search_id)
            result_count = parsed_search.get("resultCount") or parsed_search.get("result", {}).get("resultCount", 0)

            if not search_id:
                logger.error("No searchId in response")
                return None

            if result_count == 0:
                logger.debug("No elements found")
                return None

        finally:
            logger.info(f"found {result_count} element(s) with searchID = {search_id}, ")

        return search_id

    async def get_root_node_id(self):
        document = await self.get_document()
        root_node_id = document.get("result", {}).get("root", {}).get("nodeId")
        if not root_node_id:
            logger.error("Failed to get root node ID")
            return None
        return root_node_id

    async def describe_node(self, node_id):
        node_info = await self.send_request("DOM.describeNode", {"nodeId": node_id})
        parsed_node_info = await _parse_response(node_info)
        parsed_node_info.get("result", {}).get("node")
        return parsed_node_info

    async def get_box_model(self, node_id: int) -> Optional[Dict]:
        """Получить модель Box для элемента."""
        response = await self.send_request("DOM.getBoxModel", {"nodeId": node_id})
        parsed = await _parse_response(response)
        print(parsed)
        return parsed.get("result", {}).get("model")

    async def find_element_by_id(self, element_id: str) -> Optional[Dict]:
        """
        Найти элемент по ID и вернуть его данные.
        Возвращает словарь с nodeId, backendNodeId и другими данными элемента, или None если не найден.
        """
        try:
            # 1. Получаем корневой документ
            root_node_id = await self.get_root_node_id()
            # 2. Ищем элемент по ID через querySelector
            node_id = await self.query_selector(root_node_id, f"#{element_id}")

            node = await self.describe_node(node_id)
            box_model = await self.get_box_model(node_id)

            document = await self.get_document()

            return {
                "nodeId": node_id,
                "backendNodeId": node.get("backendNodeId"),
                "nodeName": node.get("nodeName"),
                "boxModel": box_model,
                "documentURL": document.get("result", {}).get("documentURL")
            }

        except Exception as e:
            logger.error(f"Error finding element by ID: {e}")
            return None

    async def get_search_results(self,search_id):
        try:
            params = {
                "searchId": search_id,
                "fromIndex": 0,
                "toIndex": 1
            }
            search_response = await self.send_request("DOM.getSearchResults", params)
            parsed_query = await _parse_response(search_response)
            while parsed_query.get("result", {}).get("nodeIds") is None:
                query_response = await self.client.receive_message()
                parsed_query = await _parse_response(query_response)
                if parsed_query.get("result", {}).get("nodeIds") is not None:
                    break

            node_id = parsed_query.get("result", {}).get("nodeIds")[0]
            return node_id


        except Exception as e:
            logger.error(f"Error finding element by search ID: {e}")
            return None

    async def find_element_by_xpath(self, xpath: str) -> Optional[Dict]:

        """
            Найти элемент по ID и вернуть его данные.
            Возвращает словарь с nodeId, backendNodeId и другими данными элемента, или None если не найден.
        """
        try:
            document = await self.get_document()
            # 1. Получаем корневой документ
            # root_node_id = await self.get_root_node_id()
            # 2. Ищем элемент по ID через querySelector

            search_id = await self.perform_search(xpath)
            print(search_id)
            logger.error(search_id)
            node_id = await self.get_search_results(search_id)

            node = await self.describe_node(node_id)
            box_model = await self.get_box_model(node_id)



            return {
                "nodeId": node_id,
                "backendNodeId": node.get("backendNodeId"),
                "nodeName": node.get("nodeName"),
                "boxModel": box_model,
                "documentURL": document.get("result", {}).get("documentURL")
            }

        except Exception as e:
            logger.error(f"Error finding element by ID: {e}")
            return None


    async def move_mouse(self, x, y):
        await self.send_request("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": x,
            "y": y,
            "modifiers": 0,
            "button": "none",
            "buttons": 0
        })


    async def press_mouse(self, x, y):
        await self.send_request("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "modifiers": 0,
            "button": "left",
            "buttons": 1,
            "clickCount": 1
        })


    async def release_mouse(self, x, y):
        await self.send_request("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "modifiers": 0,
            "button": "left",
            "buttons": 0,
            "clickCount": 1
        })


    async def get_outer_html(self, node_id: int) -> Optional[str]:
        """
        Получить outerHTML элемента по его nodeId.

        Args:
            node_id: Идентификатор узла DOM

        Returns:
            Строка с outerHTML или None в случае ошибки
        """
        try:
            response = await self.send_request("DOM.getOuterHTML", {"nodeId": node_id})
            parsed = await _parse_response(response)
            return parsed.get("result", {}).get("outerHTML")
        except Exception as e:
            logger.error(f"Failed to get outerHTML: {e}")
            return None


    async def get_inner_html(self, node_id: int) -> Optional[str]:
        """
        Получить innerHTML элемента по его nodeId.

        Args:
            node_id: Идентификатор узла DOM

        Returns:
            Строка с innerHTML или None в случае ошибки
        """
        try:
            response = await self.send_request("DOM.getInnerHTML", {"nodeId": node_id})
            parsed = await _parse_response(response)
            return parsed.get("result", {}).get("innerHTML")
        except Exception as e:
            logger.error(f"Failed to get innerHTML: {e}")
            return None


    async def get_text(self, node_id: int) -> Optional[str]:
        """
        Получить текстовое содержимое элемента (аналог getText()).

        Args:
            node_id: Идентификатор узла DOM

        Returns:
            Строка с текстовым содержимым или None в случае ошибки
        """
        try:
            # Получаем outerHTML элемента
            outer_html = await self.get_outer_html(node_id)
            if not outer_html:
                return None

            # Используем Runtime.evaluate для извлечения текста
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"(function() {{ const div = document.createElement('div'); div.innerHTML = `{outer_html}`; return div.textContent || div.innerText || ''; }})()",
                "returnByValue": True
            })

            parsed = await _parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value")
        except Exception as e:
            logger.error(f"Failed to get text content: {e}")
            return None


    async def get_text_by_selector(self, selector: str) -> Optional[str]:
        """
        Получить текстовое содержимое элемента по селектору.

        Args:
            selector: CSS селектор элемента

        Returns:
            Строка с текстовым содержимым или None если элемент не найден
        """
        try:
            root_node_id = await self.get_root_node_id()
            if not root_node_id:
                return None

            node_id = await self.query_selector(root_node_id, selector)
            if not node_id:
                return None

            return await self.get_text(node_id)
        except Exception as e:
            logger.error(f"Failed to get text by selector '{selector}': {e}")
            return None

    async def get_text_by_element(self, element_data) -> Optional[str]:
        try:
            # Получаем outerHTML элемента
            outer_html = await self.get_outer_html(element_data.get("nodeId"))
            # outer_html = await self.get_outer_html(113)
            if not outer_html:
                return None

            # Используем Runtime.evaluate для извлечения текста
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"(function() {{ const div = document.createElement('div'); div.innerHTML = `{outer_html}`; return div.textContent || div.innerText || ''; }})()",
                "returnByValue": True
            })

            parsed = await _parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value")
        except Exception as e:
            logger.error(f"Failed to get text content: {e}")
            return None


    async def get_attributes(self, node_id: int) -> Optional[Dict[str, str]]:
        """
        Получить атрибуты элемента в виде словаря.

        Args:
            node_id: Идентификатор узла DOM

        Returns:
            Словарь атрибутов или None в случае ошибки
        """
        try:
            response = await self.send_request("DOM.getAttributes", {"nodeId": node_id})
            parsed = await _parse_response(response)
            attributes = parsed.get("result", {}).get("attributes", [])

            # Преобразуем список [name1, value1, name2, value2, ...] в словарь
            return dict(zip(attributes[::2], attributes[1::2]))
        except Exception as e:
            logger.error(f"Failed to get attributes: {e}")
            return None

    async def click_element(self, element_data: Dict, wait_for_navigation=False, timeout=10) -> tuple[bool, Any | None]:
        """
        Кликнуть на элемент с опциональным ожиданием навигации.

        Args:
            element_data: Данные элемента
            wait_for_navigation: Нужно ли ждать навигации после клика
            timeout: Таймаут ожидания навигации (сек)

        Returns:
            Tuple[bool, Optional[str]]: (Успех клика, URL новой страницы или None)
        """
        global page_handler
        try:
            if not element_data:
                logger.error("No element data provided")
                return False, None

            model = element_data.get("boxModel")
            if not model:
                logger.error("No box model data")
                return False, None

            x, y = await get_center_coordinates(model)

            # Настраиваем отслеживание навигации, если нужно
            # if wait_for_navigation:
            #     page_handler = PageHandler(self.client)
            #     await page_handler.setup_page_navigation_listeners()


            await self.move_mouse(x, y)
            await self.press_mouse(x, y)
            await self.release_mouse(x, y)

            logger.debug(f"Successfully clicked element at ({x}, {y})")

            # Ожидаем навигацию, если нужно
            new_url = None
            if wait_for_navigation:
                new_url = await page_handler.wait_for_navigation(timeout)

            return True, new_url

        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False, None



    async def click_element_by_id(self, element_id: str) -> bool:
        """
        Комбинированная функция: найти элемент по ID и кликнуть на него.
        Возвращает True, если клик выполнен успешно, иначе False.
        """
        element_data = await self.find_element_by_id(element_id)
        if not element_data:
            return False

        return await self.click_element(element_data)

    # async def insert_text(self, element_data: Dict, text: str) -> bool:
    #     """
    #     Вставляет текст в указанный элемент.
    #
    #     Args:
    #         element_data: Данные элемента (содержащие nodeId), полученные из find_element_by_id или find_element_by_xpath
    #         text: Текст для вставки
    #
    #     Returns:
    #         bool: True если текст успешно вставлен, False в случае ошибки
    #     """
    #     try:
    #         if not element_data or not element_data.get("nodeId"):
    #             logger.error("No element data or nodeId provided")
    #             return False
    #
    #         node_id = element_data["nodeId"]
    #
    #         # Фокусируемся на элементе
    #         await self.send_request("DOM.focus", {"nodeId": node_id})
    #
    #         # Вводим новый текст
    #         for char in text:
    #             await self.send_request("Input.dispatchKeyEvent", {
    #                 "type": "keyDown",
    #                 "text": char,
    #                 "unmodifiedText": char,
    #                 "key": char,
    #                 "modifiers": 0
    #             })
    #             await self.send_request("Input.dispatchKeyEvent", {
    #                 "type": "keyUp",
    #                 "key": char,
    #                 "modifiers": 0
    #             })
    #
    #         logger.debug(f"Successfully inserted text '{text}' into element {node_id}")
    #         return True
    #
    #     except Exception as e:
    #         logger.error(f"Error inserting text into element: {e}")
    #         return False

    async def insert_text(self, element_data: Dict, text: str, timeout: float = 2.0) -> bool:
        """
        Вставляет текст в указанный элемент с fallback-механизмом.

        Сначала пробует быстрый JavaScript-метод, если не сработает - использует эмуляцию ввода.

        Args:
            element_data: Данные элемента (должен содержать nodeId)
            text: Текст для вставки
            timeout: Время ожидания проверки результата (в секундах)

        Returns:
            bool: True если текст успешно вставлен, False в случае ошибки
        """
        if not element_data or not element_data.get("nodeId"):
            logger.error("No element data or nodeId provided")
            return False

        node_id = element_data["nodeId"]

        # 1. Сначала пробуем быстрый JavaScript-метод
        js_success = await self._insert_text_via_javascript(node_id, text)
        if js_success :
            logger.debug(f"Successfully inserted text via JavaScript method")
            return True

        # 2. Если JavaScript-метод не сработал, пробуем медленный метод эмуляции ввода
        logger.debug("JavaScript method failed, trying input emulation...")
        input_success = await self._insert_text_via_input(node_id, text)
        if input_success:
            logger.debug(f"Successfully inserted text via input emulation")
            return True

        logger.error("All insert text methods failed")
        return False

    async def _insert_text_via_javascript(self, node_id: int, text: str) -> bool:
        """Пытается вставить текст через JavaScript"""
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"""
                    (function() {{
                        const node = document.querySelector(`[data-cdp-node-id="{node_id}"]`);
                        if (!node) return false;

                        // Для input/textarea устанавливаем value
                        if (node.value !== undefined) {{
                            node.value = `{text}`;
                        }} else {{
                            // Для contenteditable и других элементов
                            node.textContent = `{text}`;
                        }}

                        // Триггерим события
                        node.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        node.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }})()
                """,
                "returnByValue": True
            })

            parsed = await _parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value") is True
        except Exception as e:
            logger.error(f"JavaScript insert text failed: {e}")
            return False

    async def _insert_text_via_input(self, node_id: int, text: str) -> bool:
        """Вставляет текст через эмуляцию ввода с клавиатуры"""
        try:
            # Фокусируемся на элементе
            await self.send_request("DOM.focus", {"nodeId": node_id})

            # Очищаем содержимое (Ctrl+A + Backspace)
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "key": "a",
                "modifiers": 2  # Ctrl
            })
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "key": "a",
                "modifiers": 2
            })
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "key": "Backspace",
                "modifiers": 0
            })
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "key": "Backspace",
                "modifiers": 0
            })

            # Вводим текст посимвольно
            for char in text:
                await self.send_request("Input.dispatchKeyEvent", {
                    "type": "keyDown",
                    "text": char,
                    "unmodifiedText": char,
                    "key": char,
                    "modifiers": 0
                })
                await self.send_request("Input.dispatchKeyEvent", {
                    "type": "keyUp",
                    "key": char,
                    "modifiers": 0
                })

            return True
        except Exception as e:
            logger.error(f"Input emulation insert text failed: {e}")
            return False

