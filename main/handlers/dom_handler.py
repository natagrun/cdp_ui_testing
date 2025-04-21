import asyncio
import json
import logging
import time
from typing import Optional, Dict, Union, Tuple, Any

from main.handlers.base_handler import BaseHandler
from main.handlers.page_handler import PageHandler
from main.objects.element import Element

logger = logging.getLogger(__name__)

async def _parse_response(response: Union[str, Dict]) -> Dict:
    """
    Обрабатывает ответ, полученный от CDP (Chrome DevTools Protocol).
    Преобразует строку JSON в словарь, если необходимо.

    :param response: Ответ в виде строки JSON или словаря
    :return: Словарь, представляющий ответ
    """
    if isinstance(response, str):
        try:
            logger.debug("Parsing CDP response string")
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CDP response: {e}")
            return {}
    return response


async def get_center_coordinates(model: Dict) -> Union[Tuple[float, float], bool]:
    """
    Вычисляет координаты центра DOM-элемента по его box-модели.

    :param model: Словарь с моделью элемента (box model)
    :return: Кортеж координат (x, y) или False в случае ошибки
    """
    if not model:
        logger.error("No box model data provided")
        return False

    try:
        x = (model["content"][0] + model["content"][2]) / 2
        y = (model["content"][1] + model["content"][5]) / 2
        logger.debug(f"Center coordinates calculated: x={x}, y={y}")
        return x, y
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error calculating center coordinates: {e}")
        return False


async def wait_for_condition(check_function, timeout: float = 5.0, poll_frequency: float = 0.1, *args, **kwargs) -> bool:
    """
    Ожидает выполнения условия в течение заданного времени с заданной частотой опроса.

    :param check_function: Асинхронная функция, возвращающая True/False
    :param timeout: Максимальное время ожидания в секундах
    :param poll_frequency: Интервал между проверками условия в секундах
    :return: True, если условие выполнено в течение таймаута, иначе False
    """
    logger.debug(f"Waiting for condition: timeout={timeout}, poll_frequency={poll_frequency}")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if await check_function(*args, **kwargs):
                logger.info("Condition satisfied before timeout")
                return True
        except Exception as e:
            logger.error(f"Error while checking condition: {e}")
        await asyncio.sleep(poll_frequency)
    logger.warning("Condition not satisfied within timeout")
    return False


class DOMHandler(BaseHandler):
    """
    Класс-обработчик DOM, реализующий взаимодействие с Chrome DevTools Protocol.
    Предоставляет методы для получения, поиска и взаимодействия с DOM-элементами.
    """

    async def enable_dom(self) -> Dict:
        """
        Активирует протокол DOM в CDP.

        :return: Ответ в виде словаря
        """
        logger.info("Enabling DOM protocol")
        response = await self.send_request("DOM.enable")
        parsed = await _parse_response(response)
        logger.debug(f"DOM enabled: {parsed}")
        return parsed

    async def disable_dom(self) -> Dict:
        """
        Деактивирует протокол DOM в CDP.

        :return: Ответ в виде словаря
        """
        logger.info("Disabling DOM protocol")
        response = await self.send_request("DOM.disable")
        parsed = await _parse_response(response)
        logger.debug(f"DOM disabled: {parsed}")
        return parsed

    async def wait_for_page_dom_load(self, timeout: float = 10.0, inactivity_timeout: float = 3, target_class: str = "pulldown_desktop") -> None:
        """
        Ожидает полной загрузки DOM-дерева и активности страницы.

        :param timeout: Общий таймаут ожидания (секунды)
        :param inactivity_timeout: Таймаут бездействия (секунды)
        :param target_class: Имя класса элемента, по которому определяется завершение загрузки
        """
        logger.info(f"Waiting for page DOM load with timeout={timeout}s and inactivity_timeout={inactivity_timeout}s")
        start_time = time.time()
        last_activity = time.time()
        active_frames = set()
        target_elements_found = False

        while True:
            now = time.time()

            if now - start_time > timeout:
                logger.warning("Timeout expired while waiting for page DOM load")
                break

            if now - last_activity > inactivity_timeout:
                logger.info("Inactivity timeout reached during DOM load wait")
                break

            try:
                response = await asyncio.wait_for(self.client.receive_message(), timeout=1)
                last_activity = time.time()
            except asyncio.TimeoutError:
                continue

            try:
                response_data = json.loads(response)
                method = response_data.get("method")
                params = response_data.get("params", {})

                logger.debug(f"Received CDP message: {method}")

                if method == "DOM.attributeModified":
                    frame_id = params.get("nodeId")
                    if frame_id:
                        active_frames.add(frame_id)
                        logger.debug(f"Node {frame_id} attribute modified")

                elif method == "Page.frameStoppedLoading":
                    frame_id = params.get("frameId")
                    if frame_id in active_frames:
                        active_frames.remove(frame_id)
                        logger.debug(f"Frame {frame_id} stopped loading")

                elif method == "Page.frameDetached":
                    frame_id = params.get("frameId")
                    if frame_id in active_frames:
                        active_frames.remove(frame_id)
                        logger.debug(f"Frame {frame_id} detached")

                elif method == "Page.loadEventFired":
                    logger.info("Main page load event fired")

                elif method == "DOM.documentUpdated":
                    try:
                        search_result = await self.perform_search(f"//*[contains(@class, '{target_class}')]")
                        if search_result and search_result.get("resultCount", 0) > 0:
                            target_elements_found = True
                            logger.info(f"Found {search_result['resultCount']} target elements after DOM update")
                    except Exception as e:
                        logger.error(f"Error searching after DOM update: {e}")
            except Exception as e:
                logger.error(f"Failed to handle CDP message: {e}")

        logger.info("Page load and DOM readiness check completed")

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

    async def highlight_element_border(self, node_id: int, color="red", thickness="2px", duration=15.0):
        """
        Добавляет визуальную рамку к элементу по nodeId через CDP.
        """
        try:
            # Шаг 1: получаем objectId из nodeId
            resolved = await self.send_request("DOM.resolveNode", {
                "nodeId": node_id,
                "objectGroup": "highlight"
            })

            object_id = resolved.get("result", {}).get("object",{}).get("objectId")
            if not object_id:
                logger.error("Failed to resolve node to objectId")
                return False

            # Шаг 2: вызываем функцию на объекте — внимание: это строка, содержащая function, а не (function(){})()
            function_declaration = f"""
                function () {{
                    if (!this || !this.style) return false;
                    const original = this.style.border;
                    this.style.border = '{thickness} solid {color}';
                    setTimeout(() => {{
                        this.style.border = original;
                    }}, {int(duration * 1000)});
                    return true;
                }}
            """

            response = await self.send_request("Runtime.callFunctionOn", {
                "objectId": object_id,
                "functionDeclaration": function_declaration,
                "returnByValue": True
            })

            success = response.get("result", {}).get("value")
            logger.info(f"Highlight success: {success}")
            await asyncio.sleep(0.5)
            return success is True

        except Exception as e:
            logger.error(f"Highlight failed: {e}")
            return False

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

    async def find_element_by_xpath(self, xpath: str) -> Element | None:

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
            # await self.highlight_element_border(node_id,color="green")
            return Element(
                node_id=node_id,
                backend_node_id=node.get("backendNodeId"),
                node_name=node.get("nodeName"),
                box_model=box_model,
                document_url=document.get("result", {}).get("documentURL")
            )

        except Exception as e:
            logger.error(f"Error finding element by ID: {e}")
            return None

    async def focus_on_element(self, element):
        try:
            response = await self.send_request("DOM.focus", {"nodeId": element.node_id})
            parsed = await _parse_response(response)
            print(parsed)
            return parsed.get("result", {}).get("innerHTML")
        except Exception as e:
            logger.error(f"Failed to get innerHTML: {e}")
            return None

    async def move_mouse_on_element(self, element):
        model = element.box_model
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
        await self.wait_for_page_dom_load()

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

    async def get_text(self, element_data) -> bool | None | Any:
        """
        Получить текстовое содержимое элемента (аналог getText()).

        Args:
            node_id: Идентификатор узла DOM

        Returns:
            Строка с текстовым содержимым или None в случае ошибки
            :param element_data:
        """
        try:
            if not element_data:
                logger.error("No element data provided")
                return False

            node_id = element_data.get("nodeId")
            if not node_id:
                logger.error("No node id data")
                return False
            await self.highlight_element_border(node_id)

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

    async def get_text_by_element(self, element) -> Optional[str]:
        try:
            # Получаем outerHTML элемента
            outer_html = await self.get_outer_html(element.node_id)
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

    async def get_attributes(self, element) -> Optional[Dict[str, str]]:
        """
        Получить атрибуты элемента в виде словаря.

        Args:
            node_id: Идентификатор узла DOM

        Returns:
            Словарь атрибутов или None в случае ошибки
            :param element:
            :param element_data:
        """
        try:

            response = await self.send_request("DOM.getAttributes", {"nodeId": element.node_id})
            parsed = await _parse_response(response)
            attributes = parsed.get("result", {}).get("attributes", [])

            # Преобразуем список [name1, value1, name2, value2, ...] в словарь
            return dict(zip(attributes[::2], attributes[1::2]))
        except Exception as e:
            logger.error(f"Failed to get attributes: {e}")
            return None

    async def click_element(self, element) -> bool:
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
            if not element:
                logger.error("No element data provided")
                return False

            model = element.box_model
            if not model:
                logger.error("No box model data")
                return False
            node_id = element.node_id
            if not node_id:
                logger.error("No node id data")
                return False
            await self.highlight_element_border(node_id)
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

    async def insert_text(self, element, text: str) -> bool:
        """
        Вставляет текст в указанный элемент с fallback-механизмом.

        Сначала пробует быстрый JavaScript-метод, если не сработает - использует эмуляцию ввода.

        Args:
            element: Данные элемента (должен содержать nodeId)
            text: Текст для вставки

        Returns:
            bool: True если текст успешно вставлен, False в случае ошибки
            :param text:
            :param element:
        """
        if not element or not element.node_id:
            logger.error("No element data or nodeId provided")
            return False

        node_id = element.node_id

        await self.focus_on_element(element)

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
        """Вставляет текст в элемент напрямую через JS, используя objectId"""
        try:
            # Получаем objectId из nodeId
            resolved = await self.send_request("DOM.resolveNode", {
                "nodeId": node_id
            })
            object_id = resolved.get("result", {}).get("objectId")
            if not object_id:
                logger.error("Cannot resolve objectId from nodeId")
                return False

            # Выполняем вставку
            js_func = f"""
                function () {{
                    if (!this) return false;
                    if ('value' in this) {{
                        this.value = `{text}`;
                    }} else if (this.isContentEditable) {{
                        this.innerText = `{text}`;
                    }} else {{
                        return false;
                    }}
                    this.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    this.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
            """

            response = await self.send_request("Runtime.callFunctionOn", {
                "objectId": object_id,
                "functionDeclaration": js_func,
                "returnByValue": True
            })

            return response.get("result", {}).get("value") is True

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

    async def clear_field(self, node_id: int) -> bool:
        """Очищает содержимое элемента через эмуляцию Ctrl+A + Backspace"""
        try:
            await self.send_request("DOM.focus", {"nodeId": node_id})

            # Выделить всё (Ctrl+A)
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyDown", "key": "a", "modifiers": 2
            })
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyUp", "key": "a", "modifiers": 2
            })

            # Удалить (Backspace)
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyDown", "key": "Backspace", "modifiers": 0
            })
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyUp", "key": "Backspace", "modifiers": 0
            })

            return True
        except Exception as e:
            logger.error(f"Failed to clear field: {e}")
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

    async def scroll_to_element(self, element) -> bool:
        """
        Прокручивает страницу к указанному элементу.

        Args:
            element_data: Данные элемента (должен содержать nodeId)

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        if not element or not element.node_id:
            logger.error("No element data or nodeId provided")
            return False

        try:
            model = element.box_model
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

    async def smooth_scroll_to_element(self, element) -> bool:
        """
        Плавно прокручивает страницу к указанному элементу.

        Args:
            element_data: Данные элемента (должен содержать nodeId)

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        if not element or not element.node_id:
            logger.error("No element data or nodeId provided")
            return False

        try:
            # Пробуем через JavaScript для плавной прокрутки
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"""
                    (function() {{
                        const node = document.querySelector('[data-cdp-node-id="{element.node_id}"]');
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

    async def is_element_visible(self, node_id: int) -> bool:
        """
        Проверяет, видим ли элемент в DOM (display, visibility, opacity).
        """
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"""
                    (function() {{
                        const el = document.querySelector('[data-cdp-node-id=\"{node_id}\"]');
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        return (
                            style && 
                            style.display !== 'none' &&
                            style.visibility !== 'hidden' &&
                            style.opacity !== '0'
                        );
                    }})()
                """,
                "returnByValue": True
            })
            return response.get("result", {}).get("result", {}).get("value") is True
        except Exception as e:
            logger.error(f"Error checking visibility: {e}")
            return False

    async def is_element_clickable(self, node_id: int) -> bool:
        """
        Проверяет, кликабелен ли элемент (видим и не заблокирован).
        """
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"""
                    (function() {{
                        const el = document.querySelector('[data-cdp-node-id=\"{node_id}\"]');
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return (
                            style.display !== 'none' &&
                            style.visibility !== 'hidden' &&
                            style.opacity !== '0' &&
                            !el.disabled &&
                            rect.width > 0 &&
                            rect.height > 0
                        );
                    }})()
                """,
                "returnByValue": True
            })
            return response.get("result", {}).get("result", {}).get("value") is True
        except Exception as e:
            logger.error(f"Error checking clickability: {e}")
            return False
