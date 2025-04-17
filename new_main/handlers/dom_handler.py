import asyncio
import json
import logging
import time
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

    async def wait_for_page_dom_load(self, timeout=30, target_class="pulldown_desktop"):
        """Ожидание завершения загрузки страницы, всех фреймов И появления целевых элементов."""
        print("Waiting for dom load and target elements...")
        start_time = time.time()
        active_frames = set()  # Для отслеживания загружающихся фреймов
        target_elements_found = False

        while True:
            # Проверка таймаута
            if time.time() - start_time > timeout:
                print("Page dom timeout reached!")
                break

            try:
                response = await asyncio.wait_for(self.client.receive_message(), timeout=1)
            except asyncio.TimeoutError:
                # Если нет событий, проверяем загрузку фреймов и наличие элементов
                if not active_frames:
                    # Проверяем наличие целевых элементов
                    if not target_elements_found:
                        try:
                            # Ищем элементы с нужным классом
                            search_result = await self.client.send(
                                "DOM.performSearch",
                                {"query": f'//*[contains(@class, "{target_class}")]'}
                            )
                            if search_result.get("resultCount", 0) > 0:
                                target_elements_found = True
                                print(f"Found {search_result['resultCount']} target elements")
                            else:
                                print("Target elements not found yet, continuing...")
                                continue
                        except Exception as e:
                            print(f"Error searching for elements: {e}")
                            continue
                    else:
                        print("All frames loaded and target elements found!")
                        break
                continue

            response_data = json.loads(response)
            method = response_data.get("method")

            if method == "DOM.attributeModified":
                frame_id = response_data["params"]["nodeId"]
                active_frames.add(frame_id)
                print(f"node {frame_id} edited parameters")

            elif method == "Page.frameStoppedLoading":
                frame_id = response_data["params"]["frameId"]
                if frame_id in active_frames:
                    active_frames.remove(frame_id)
                    print(f"Frame {frame_id} stopped loading")

            elif method == "Page.frameDetached":
                frame_id = response_data["params"]["frameId"]
                if frame_id in active_frames:
                    active_frames.remove(frame_id)
                    print(f"Frame {frame_id} detached")

            elif method == "Page.loadEventFired":
                print("Main page load event fired")

            # Дополнительно проверяем появление элементов при каждом изменении DOM
            elif method == "DOM.documentUpdated":
                try:
                    search_result = await self.client.send(
                        "DOM.performSearch",
                        {"query": f'//*[contains(@class, "{target_class}")]'}
                    )
                    if search_result.get("resultCount", 0) > 0:
                        target_elements_found = True
                        print(f"Found {search_result['resultCount']} target elements after DOM update")
                except Exception as e:
                    print(f"Error searching after DOM update: {e}")

        print("Page load and element check completed!")

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

    async def get_search_results(self, search_id):
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

    async def focus_on_element(self, element_data):
        try:
            response = await self.send_request("DOM.focus", {"nodeId": element_data.get("nodeId")})
            parsed = await _parse_response(response)
            print(parsed)
            return parsed.get("result", {}).get("innerHTML")
        except Exception as e:
            logger.error(f"Failed to get innerHTML: {e}")
            return None

    async def move_mouse_on_element(self, element_data):
        model = element_data.get("boxModel")
        if not model:
            logger.error("No box model data")
            return False

        x, y = await get_center_coordinates(model)

        await self.send_request("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": x,
            "y": y,
            "modifiers": 0,
            "button": "none",
            "buttons": 0
        })

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

    async def get_attributes(self, element_data: Dict) -> Optional[Dict[str, str]]:
        """
        Получить атрибуты элемента в виде словаря.

        Args:
            node_id: Идентификатор узла DOM

        Returns:
            Словарь атрибутов или None в случае ошибки
            :param element_data:
        """
        try:

            response = await self.send_request("DOM.getAttributes", {"nodeId": element_data.get("nodeId")})
            parsed = await _parse_response(response)
            attributes = parsed.get("result", {}).get("attributes", [])

            # Преобразуем список [name1, value1, name2, value2, ...] в словарь
            return dict(zip(attributes[::2], attributes[1::2]))
        except Exception as e:
            logger.error(f"Failed to get attributes: {e}")
            return None

    async def click_element(self, element_data: Dict, wait_for_navigation=False, timeout=10) -> bool:
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
                return False

            model = element_data.get("boxModel")
            if not model:
                logger.error("No box model data")
                return False

            x, y = await get_center_coordinates(model)

            # Настраиваем отслеживание навигации, если нужно
            # if wait_for_navigation:
            #     page_handler = PageHandler(self.client)
            #     await page_handler.setup_page_navigation_listeners()

            await self.move_mouse(x, y)
            await self.press_mouse(x, y)
            await self.release_mouse(x, y)

            logger.error(f"Successfully clicked element at ({x}, {y})")

            page_handler = PageHandler(self.client)
            await page_handler.wait_for_page_dom_load(10, 3)
            return True

        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False

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

        await self.focus_on_element(element_data)

        # 1. Сначала пробуем быстрый JavaScript-метод
        js_success = await self._insert_text_via_javascript(node_id, text)
        if js_success:
            logger.debug(f"Successfully inserted text via JavaScript method")
            return True

        # 2. Если JavaScript-метод не сработал, пробуем медленный метод эмуляции ввода
        logger.debug("JavaScript method failed, trying input emulation...")
        input_success = await self._insert_text_via_input(node_id, text)

        page_handler2 = PageHandler(self.client)
        await page_handler2.wait_for_page_dom_load(2)
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

    async def scroll_to_coordinates(self, x: int, y: int) -> bool:
        """
        Прокручивает страницу к указанным координатам.

        Args:
            x: Горизонтальная координата
            y: Вертикальная координата

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"window.scrollTo({x}, {y})",
                "awaitPromise": False
            })
            parsed = await _parse_response(response)
            if parsed.get("exceptionDetails"):
                logger.error(f"Scroll failed: {parsed.get('exceptionDetails')}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error scrolling to coordinates: {e}")
            return False

    async def scroll_to_element(self, element_data: Dict) -> bool:
        """
        Прокручивает страницу к указанному элементу.

        Args:
            element_data: Данные элемента (должен содержать nodeId)

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        if not element_data or not element_data.get("nodeId"):
            logger.error("No element data or nodeId provided")
            return False

        try:
            model = element_data.get("boxModel")
            if not model:
                logger.error("No box model data")
                return False

            x, y = await get_center_coordinates(model)
            await self.scroll_to_coordinates(x, y)

        except Exception as ex:
            logger.error(f"JavaScript scroll fallback also failed: {ex}")
            return False

    async def scroll_by(self, delta_x: int = 0, delta_y: int = 0) -> bool:
        """
        Прокручивает страницу на указанное количество пикселей.

        Args:
            delta_x: Горизонтальное смещение
            delta_y: Вертикальное смещение

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        try:
            # Вариант 1: Через Input.synthesizeScrollGesture (наиболее реалистично)
            response = await self.send_request("Input.synthesizeScrollGesture", {
                "x": 100,  # Стартовая позиция (не важна для простой прокрутки)
                "y": 100,
                "xDistance": delta_x,
                "yDistance": -delta_y,  # Отрицательное значение потому что в CDP направление обратное
                "speed": 1000
            })
            parsed = await _parse_response(response)
            if not parsed.get("error"):
                return True

            # Вариант 2: Через JavaScript (fallback)
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"window.scrollBy({delta_x}, {delta_y})",
                "awaitPromise": False
            })
            parsed = await _parse_response(response)
            return not parsed.get("exceptionDetails")
        except Exception as e:
            logger.error(f"Error scrolling by delta: {e}")
            return False

    async def smooth_scroll_to_element(self, element_data: Dict) -> bool:
        """
        Плавно прокручивает страницу к указанному элементу.

        Args:
            element_data: Данные элемента (должен содержать nodeId)

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        if not element_data or not element_data.get("nodeId"):
            logger.error("No element data or nodeId provided")
            return False

        try:
            # Пробуем через JavaScript для плавной прокрутки
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"""
                    (function() {{
                        const node = document.querySelector('[data-cdp-node-id="{element_data["nodeId"]}"]');
                        if (node) {{
                            node.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center',
                                inline: 'center'
                            }});
                        }}
                        return !!node;
                    }})()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            parsed = await _parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value") is True
        except Exception as e:
            logger.error(f"Error smooth scrolling to element: {e}")
            return False

    # async def handle_js_dialog(self, accept: bool = True, prompt_text: str = ""):
    #     try:
    #         response = await self.client.receive_message()
    #         data = json.loads(response)
    #
    #         if data.get("method") == "Page.javascriptDialogOpening":
    #             logger.warning(f"JS Dialog appeared: {data['params'].get('message')}")
    #
    #             await self.send_request("Page.handleJavaScriptDialog", {
    #                 "accept": accept,
    #                 "promptText": prompt_text
    #             })
    #
    #             logger.info("Dialog handled")
    #
    #     except Exception as e:
    #         logger.error(f"Error handling JS dialog: {e}")

    async def is_alert_open(self) -> bool:
        try:
            # Отправляем запрос на закрытие диалога
            response = await self.send_request("Page.handleJavaScriptDialog", {
                "accept": True
            })

            await self.client.receive_message()
            await self.client.receive_message()
            pa = PageHandler(self.client)
            await pa.wait_for_page_dom_load(5,2)
            return True  # Алерт был и мы его обработали

        except Exception as e:
            if "No dialog is showing" in str(e):
                return False
            logger.error(f"Error while checking alert: {e}")
            return False