import asyncio
import logging
import time
from typing import Optional, Dict

from main.handlers.base_handler import BaseHandler
from main.handlers.page_handler import PageHandler
from main.objects.element import Element
from main.utils.math import get_center_coordinates
from main.utils.parser import parse_response

logger = logging.getLogger(__name__)

async def wait_for_condition(check_function, timeout: float = 5.0, poll_frequency: float = 0.1, *args,
                             **kwargs) -> bool:
    """
    Ожидает выполнения условия в течение заданного времени с заданной частотой опроса.

    :param check_function: Асинхронная функция, возвращающая True/False
    :param timeout: Максимальное время ожидания в секундах
    :param poll_frequency: Интервал между проверками условия в секундах
    :return: True, если условие выполнено в течение таймаута, иначе False
    """
    logger.debug(f"Waiting for condition with timeout={timeout}s and poll_frequency={poll_frequency}s")
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
    Обработчик взаимодействия с DOM с использованием протокола Chrome DevTools Protocol (CDP).
    Предоставляет API для поиска, получения и взаимодействия с элементами DOM.
    """

    async def enable_dom(self) -> Dict:
        """
        Активирует поддержку домена DOM в CDP.

        :return: Ответ от CDP в виде словаря
        """
        logger.info("Enabling DOM domain")
        response = await self.send_request("DOM.enable")
        parsed = await parse_response(response)
        logger.debug(f"DOM domain enabled: {parsed}")
        return parsed

    async def disable_dom(self) -> Dict:
        """
        Деактивирует поддержку домена DOM в CDP.

        :return: Ответ от CDP в виде словаря
        """
        logger.info("Disabling DOM domain")
        response = await self.send_request("DOM.disable")
        parsed = await parse_response(response)
        logger.debug(f"DOM domain disabled: {parsed}")
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
                response_data = await parse_response(response)
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
        """
        Получает корневой документ DOM.

        :param depth: Глубина рекурсивного получения узлов
        :return: DOM-документ в виде словаря
        """
        logger.info("Requesting root document")
        response = await self.send_request("DOM.getDocument", {"depth": depth})
        parsed = await parse_response(response)
        logger.debug(f"Document received: {parsed}")
        return parsed

    async def get_root_node_id(self) -> Optional[int]:
        """
        Возвращает идентификатор корневого узла DOM.

        :return: nodeId корня DOM или None при ошибке
        """
        logger.info("Getting root node ID")
        document = await self.get_document()
        root_node_id = document.get("result", {}).get("root", {}).get("nodeId")
        if not root_node_id:
            logger.error("Failed to retrieve root node ID")
            return None
        return root_node_id

    async def query_selector(self, root_node_id: int, selector: str) -> Optional[int]:
        """
        Выполняет querySelector для поиска элемента по CSS-селектору.

        :param root_node_id: nodeId корня, откуда начинать поиск
        :param selector: CSS-селектор
        :return: nodeId найденного элемента или None
        """
        logger.info(f"Querying selector: {selector} under node {root_node_id}")
        query_response = await self.send_request("DOM.querySelector", {
            "nodeId": root_node_id,
            "selector": selector
        })
        parsed_query = await parse_response(query_response)

        while parsed_query.get("result", {}).get("nodeId") is None:
            query_response = await self.client.receive_message()
            parsed_query = await parse_response(query_response)

        node_id = parsed_query.get("result", {}).get("nodeId")
        if not node_id:
            logger.warning(f"Element not found for selector: {selector}")
            return None
        return node_id

    async def perform_search(self, xpath: str) -> Optional[str]:
        """
        Выполняет XPath-поиск по DOM.

        :param xpath: XPath выражение для поиска элемента
        :return: Идентификатор поиска searchId или None при ошибке
        """
        logger.info(f"Performing DOM search with XPath: {xpath}")
        try:
            params = {
                "query": xpath,
                "includeUserAgentShadowDOM": True
            }
            search_response = await self.send_request("DOM.performSearch", params)
            parsed_search = await parse_response(search_response)

            search_id = parsed_search.get("searchId") or parsed_search.get("result", {}).get("searchId")
            result_count = parsed_search.get("resultCount") or parsed_search.get("result", {}).get("resultCount", 0)

            if not search_id:
                logger.error("No searchId returned from performSearch")
                return None

            logger.info(f"Found {result_count} elements using XPath search. searchId={search_id}")
            return search_id
        except Exception as e:
            logger.error(f"Error during perform_search: {e}")
            return None

    async def get_search_results(self, search_id: str) -> Optional[int]:
        """
        Получает nodeId первого элемента из результатов поиска по searchId.

        :param search_id: Идентификатор поиска
        :return: nodeId первого найденного элемента или None
        """
        logger.info(f"Fetching search results for searchId: {search_id}")
        try:
            params = {
                "searchId": search_id,
                "fromIndex": 0,
                "toIndex": 1
            }
            search_response = await self.send_request("DOM.getSearchResults", params)
            parsed_query = await parse_response(search_response)

            node_ids = parsed_query.get("result", {}).get("nodeIds")
            if not node_ids:
                logger.warning("No nodeIds found in search results")
                return None

            logger.debug(f"Found nodeId in search results: {node_ids[0]}")
            return node_ids[0]
        except Exception as e:
            logger.error(f"Error retrieving search results: {e}")
            return None

    async def describe_node(self, node_id: int) -> Optional[Dict]:
        """
        Возвращает описание DOM-узла по nodeId.

        :param node_id: Идентификатор узла DOM
        :return: Словарь с описанием узла или None
        """
        logger.info(f"Describing node {node_id}")
        try:
            node_info = await self.send_request("DOM.describeNode", {"nodeId": node_id})
            parsed_node_info = await parse_response(node_info)
            return parsed_node_info.get("result", {}).get("node")
        except Exception as e:
            logger.error(f"Error describing node: {e}")
            return None

    async def get_box_model(self, node_id: int) -> Optional[Dict]:
        """
        Получает box model (модель границ) элемента.

        :param node_id: Идентификатор узла DOM
        :return: Словарь с моделью box или None
        """
        logger.info(f"Getting box model for node {node_id}")
        try:
            response = await self.send_request("DOM.getBoxModel", {"nodeId": node_id})
            parsed = await parse_response(response)
            return parsed.get("result", {}).get("model")
        except Exception as e:
            logger.error(f"Failed to get box model: {e}")
            return None

    async def find_element_by_xpath(self, xpath: str) -> Optional[Element]:
        """
        Ищет DOM-элемент по XPath и возвращает объект Element.

        :param xpath: XPath выражение
        :return: Объект Element или None
        """
        logger.info(f"Finding element by XPath: {xpath}")
        try:
            document = await self.get_document()
            search_id = await self.perform_search(xpath)
            if not search_id:
                return None

            node_id = await self.get_search_results(search_id)
            if not node_id:
                return None

            node = await self.describe_node(node_id)
            box_model = await self.get_box_model(node_id)

            element = Element(
                node_id=node_id,
                backend_node_id=node.get("backendNodeId"),
                node_name=node.get("nodeName"),
                box_model=box_model,
                document_url=document.get("result", {}).get("documentURL"),
                dom_handler=self
            )
            logger.debug(f"Element found: {element}")
            return element
        except Exception as e:
            logger.error(f"Error finding element by XPath: {e}")
            return None

    async def highlight_element_border(self, node_id: int, color="red", thickness="2px",
                                       duration: float = 15.0) -> bool:
        """
        Визуально подсвечивает DOM-элемент с помощью CSS-рамки.

        :param node_id: Идентификатор узла DOM
        :param color: Цвет рамки
        :param thickness: Толщина рамки
        :param duration: Время отображения рамки в секундах
        :return: True если операция выполнена успешно, иначе False
        """
        logger.info(f"Highlighting element {node_id} with border color={color}, thickness={thickness}")
        try:
            resolved = await self.send_request("DOM.resolveNode", {
                "nodeId": node_id,
                "objectGroup": "highlight"
            })
            object_id = resolved.get("result", {}).get("object", {}).get("objectId")
            if not object_id:
                logger.error("Could not resolve node to objectId")
                return False

            function_declaration = f"""
                    function () {{
                        if (!this || !this.style) return false;
                        const original = this.style.border;
                        this.style.border = '{thickness} solid {color}';
                        setTimeout(() => {{ this.style.border = original; }}, {int(duration * 1000)});
                        return true;
                    }}
                """

            response = await self.send_request("Runtime.callFunctionOn", {
                "objectId": object_id,
                "functionDeclaration": function_declaration,
                "returnByValue": True
            })

            success = response.get("result", {}).get("value")
            logger.debug(f"Highlight result: {success}")
            await asyncio.sleep(0.5)
            return success is True
        except Exception as e:
            logger.error(f"Highlight failed: {e}")
            return False

    async def move_mouse(self, x: float, y: float) -> None:
        """
        Перемещает указатель мыши в указанные координаты.

        :param x: Горизонтальная координата
        :param y: Вертикальная координата
        """
        logger.info(f"Moving mouse to ({x}, {y})")
        try:
            await self.send_request("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": x,
                "y": y,
                "modifiers": 0,
                "button": "none",
                "buttons": 0
            })
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")

    async def move_mouse_on_element(self, element: Element) -> bool:
        """
        Перемещает указатель мыши на центр DOM-элемента.

        :param element: Объект Element с box_model
        :return: True если перемещение выполнено успешно
        """
        logger.info(f"Moving mouse to element: {element.node_id}")
        if not element.box_model:
            logger.error("Element has no box model")
            return False
        try:
            x, y = await get_center_coordinates(element.box_model)
            await self.move_mouse(x, y)
            return True
        except Exception as e:
            logger.error(f"Failed to move mouse to element: {e}")
            return False

    async def press_mouse(self, x: float, y: float) -> None:
        """
        Имитирует нажатие кнопки мыши.

        :param x: Координата X
        :param y: Координата Y
        """
        logger.info(f"Pressing mouse at ({x}, {y})")
        try:
            await self.send_request("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "modifiers": 0,
                "button": "left",
                "buttons": 1,
                "clickCount": 1
            })
        except Exception as e:
            logger.error(f"Mouse press failed: {e}")

    async def release_mouse(self, x: float, y: float) -> None:
        """
        Имитирует отпускание кнопки мыши.

        :param x: Координата X
        :param y: Координата Y
        """
        logger.info(f"Releasing mouse at ({x}, {y})")
        try:
            await self.send_request("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "modifiers": 0,
                "button": "left",
                "buttons": 0,
                "clickCount": 1
            })
        except Exception as e:
            logger.error(f"Mouse release failed: {e}")

    async def click_element(self, element: Element) -> bool:
        """
        Выполняет клик по DOM-элементу, используя эмуляцию движения и нажатия мыши.

        :param element: Объект DOM-элемента
        :return: True, если клик успешно выполнен
        """
        logger.info(f"Clicking on element: {element.node_id}")
        if not element or not element.box_model:
            logger.error("Element or its box model is not provided")
            return False
        try:
            await self.highlight_element_border(element.node_id)
            x, y = await get_center_coordinates(element.box_model)
            await self.move_mouse(x, y)
            await self.press_mouse(x, y)
            await self.release_mouse(x, y)

            logger.info(f"Click on element {element.node_id} at ({x}, {y}) completed")
            page_handler = PageHandler(self.client)
            await page_handler.wait_for_page_dom_load(timeout=10, inactivity_timeout=3)
            return True
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return False

    async def focus_on_element(self, element: Element) -> Optional[str]:
        """
        Устанавливает фокус на указанный DOM-элемент.

        :param element: Объект DOM-элемента
        :return: innerHTML элемента, если успешно, иначе None
        """
        logger.info(f"Focusing on element: {element.node_id}")
        try:
            response = await self.send_request("DOM.focus", {"nodeId": element.node_id})
            parsed = await parse_response(response)
            return parsed.get("result", {}).get("innerHTML")
        except Exception as e:
            logger.error(f"Failed to focus on element: {e}")
            return None

    async def _insert_text_via_javascript(self, node_id: int, text: str) -> bool:
        """
        Вставляет текст в элемент с помощью JavaScript через objectId.

        :param node_id: Идентификатор DOM-узла
        :param text: Вставляемый текст
        :return: True, если успешно
        """
        logger.debug(f"Inserting text via JavaScript into node {node_id}")
        try:
            resolved = await self.send_request("DOM.resolveNode", {"nodeId": node_id})
            object_id = resolved.get("result", {}).get("objectId")
            if not object_id:
                logger.error("Failed to resolve objectId from nodeId")
                return False

            js_func = f"""
                    function () {{
                        if (!this) return false;
                        if ('value' in this) {{ this.value = `{text}`; }}
                        else if (this.isContentEditable) {{ this.innerText = `{text}`; }}
                        else {{ return false; }}
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
            logger.error(f"JavaScript text insertion failed: {e}")
            return False

    async def _insert_text_via_input(self, node_id: int, text: str) -> bool:
        """
        Вставляет текст с помощью эмуляции ввода с клавиатуры.

        :param node_id: Идентификатор DOM-узла
        :param text: Вставляемый текст
        :return: True, если успешно
        """
        logger.debug(f"Inserting text via input emulation into node {node_id}")
        try:
            await self.send_request("DOM.focus", {"nodeId": node_id})

            await self.send_request("Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "modifiers": 2})
            await self.send_request("Input.dispatchKeyEvent", {"type": "keyUp", "key": "a", "modifiers": 2})
            await self.send_request("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Backspace"})
            await self.send_request("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Backspace"})

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
            logger.error(f"Input emulation text insertion failed: {e}")
            return False

    async def insert_text(self, element: Element, text: str) -> bool:
        """
        Вставляет текст в элемент. Сначала через JavaScript, затем через эмуляцию клавиатуры.

        :param element: Объект DOM-элемента
        :param text: Текст для вставки
        :return: True, если вставка выполнена
        """
        logger.info(f"Inserting text into element {element.node_id}")
        if not element or not element.node_id:
            logger.error("Element or node_id is missing")
            return False

        await self.focus_on_element(element)

        if await self._insert_text_via_javascript(element.node_id, text):
            logger.info("Text inserted via JavaScript")
            return True

        logger.warning("JavaScript insertion failed, trying input emulation")
        if await self._insert_text_via_input(element.node_id, text):
            logger.info("Text inserted via input emulation")
            return True

        logger.error("Failed to insert text using both methods")
        return False

    async def scroll_to_coordinates(self, x: int, y: int) -> bool:
        """
        Прокручивает окно к указанным координатам.

        :param x: Координата X
        :param y: Координата Y
        :return: True если прокрутка выполнена успешно
        """
        logger.info(f"Scrolling to coordinates ({x}, {y})")
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"window.scrollTo({x}, {y})",
                "awaitPromise": False
            })
            parsed = await parse_response(response)
            if parsed.get("exceptionDetails"):
                logger.error(f"Scroll failed: {parsed['exceptionDetails']}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error during scroll: {e}")
            return False

    async def scroll_by(self, delta_x: int = 0, delta_y: int = 0) -> bool:
        """
        Прокручивает страницу на заданное смещение.

        :param delta_x: Смещение по X
        :param delta_y: Смещение по Y
        :return: True если прокрутка выполнена
        """
        logger.info(f"Scrolling by delta x={delta_x}, y={delta_y}")
        try:
            response = await self.send_request("Input.synthesizeScrollGesture", {
                "x": 100,
                "y": 100,
                "xDistance": delta_x,
                "yDistance": -delta_y,
                "speed": 1000
            })
            parsed = await parse_response(response)
            if not parsed.get("error"):
                return True

            logger.warning("Fallback to JS scroll")
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"window.scrollBy({delta_x}, {delta_y})",
                "awaitPromise": False
            })
            parsed = await parse_response(response)
            return not parsed.get("exceptionDetails")
        except Exception as e:
            logger.error(f"Scroll by delta failed: {e}")
            return False

    async def smooth_scroll_to_element(self, element: Element) -> bool:
        """
        Плавно прокручивает страницу к элементу.

        :param element: Объект DOM-элемента
        :return: True если прокрутка выполнена
        """
        logger.info(f"Smooth scrolling to element {element.node_id}")
        if not element or not element.node_id:
            logger.error("Element or node_id is missing")
            return False
        try:
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
            parsed = await parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value") is True
        except Exception as e:
            logger.error(f"Smooth scroll to element failed: {e}")
            return False

    async def clear_field(self, node_id: int) -> bool:
        """
        Очищает содержимое элемента через имитацию Ctrl+A + Backspace.

        :param node_id: Идентификатор DOM-узла
        :return: True, если очистка прошла успешно
        """
        logger.info(f"Clearing input field for node {node_id}")
        try:
            await self.send_request("DOM.focus", {"nodeId": node_id})
            await self.send_request("Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "modifiers": 2})
            await self.send_request("Input.dispatchKeyEvent", {"type": "keyUp", "key": "a", "modifiers": 2})
            await self.send_request("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Backspace"})
            await self.send_request("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Backspace"})
            logger.debug("Field cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear input field: {e}")
            return False

    async def is_alert_open(self) -> bool:
        """
        Проверяет наличие открытого JavaScript-диалога и закрывает его при необходимости.

        :return: True, если предупреждение было открыто и обработано, иначе False
        """
        logger.info("Checking for JavaScript alert")
        try:
            await self.send_request("Page.handleJavaScriptDialog", {"accept": True})
            await self.client.receive_message()
            await self.client.receive_message()
            pa = PageHandler(self.client)
            await pa.wait_for_page_dom_load(5, 2)
            logger.info("Alert detected and handled")
            return True
        except Exception as e:
            if "No dialog is showing" in str(e):
                logger.debug("No alert currently active")
                return False
            logger.error(f"Error while checking alert: {e}")
            return False

    async def is_element_visible(self, node_id: int) -> bool:
        """
        Проверяет, видим ли элемент в DOM (по стилям: display, visibility, opacity).

        :param node_id: Идентификатор DOM-узла
        :return: True, если элемент видим
        """
        logger.info(f"Checking visibility of node {node_id}")
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"""
                        (function() {{
                            const el = document.querySelector('[data-cdp-node-id="{node_id}"]');
                            if (!el) return false;
                            const style = window.getComputedStyle(el);
                            return (
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
            logger.error(f"Failed to check element visibility: {e}")
            return False

    async def is_element_clickable(self, node_id: int) -> bool:
        """
        Проверяет, кликабелен ли элемент: видим, не заблокирован и имеет ненулевой размер.

        :param node_id: Идентификатор DOM-узла
        :return: True, если элемент кликабелен
        """
        logger.info(f"Checking click ability of node {node_id}")
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"""
                        (function() {{
                            const el = document.querySelector('[data-cdp-node-id="{node_id}"]');
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
            logger.error(f"Failed to check element click ability: {e}")
            return False
