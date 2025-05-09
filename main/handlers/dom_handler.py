import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any

from main.handlers.base_handler import BaseHandler
from main.handlers.input_handler import InputHandler
from main.handlers.page_handler import PageHandler
from main.handlers.runtime_handler import RuntimeHandler
from main.objects.element import Element
from main.utils.parser import parse_response


class DOMHandler(BaseHandler):
    """
    Класс-обработчик DOM, реализующий взаимодействие с Chrome DevTools Protocol.
    Предоставляет методы для получения, поиска и взаимодействия с DOM-элементами.
    """

    def __init__(self, client, logger_obj):
        super().__init__(client,logger_obj)
        self.log = logger_obj.getChild("DOMHandler")
        self._runtime = RuntimeHandler(client, logger_obj)

    async def enable_dom(self) -> Dict:
        """
        Активирует протокол DOM в CDP.

        :return: Ответ в виде словаря
        """
        self.log.info("Активируем протокол DOM")
        response = await self.send_request("DOM.enable")
        parsed = await parse_response(response)
        self.log.debug(f"DOM enabled: {parsed}")
        return parsed

    async def disable_dom(self) -> Dict:
        """
        Деактивирует протокол DOM в CDP.

        :return: Ответ в виде словаря
        """
        self.log.info("Деактивируем протокол DOM")
        response = await self.send_request("DOM.disable")
        parsed = await parse_response(response)
        self.log.debug(f"DOM деактивирован: {parsed}")
        return parsed

    async def wait_for_condition(self, check_function, timeout: float = 5.0, poll_frequency: float = 0.1, *args,
                                 **kwargs) -> bool:
        """
        Ожидает выполнения условия в течение заданного времени с заданной частотой опроса.

        :param check_function: Асинхронная функция, возвращающая True/False
        :param timeout: Максимальное время ожидания в секундах
        :param poll_frequency: Интервал между проверками условия в секундах
        :return: True, если условие выполнено в течение таймаута, иначе False
        """
        self.log.debug(f"Ожидает выполнения условия в течение {timeout}, с интервалом {poll_frequency}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if await check_function(*args, **kwargs):
                    self.log.info("Условие выполнилось до таймаута")
                    return True
            except Exception as e:
                self.log.error(f"Ошибка во время проверки условия: {e}")
            await asyncio.sleep(poll_frequency)
        self.log.warning("Условие не выполнилось за время таймаута")
        return False

    async def wait_for_page_dom_load(self, timeout: float = 10.0, inactivity_timeout: float = 3,
                                     target_class: str = "pulldown_desktop") -> None:
        """
        Ожидает полной загрузки DOM-дерева и активности страницы.

        :param timeout: Общий таймаут ожидания (секунды)
        :param inactivity_timeout: Таймаут бездействия (секунды)
        :param target_class: Имя класса элемента, по которому определяется завершение загрузки
        """
        self.log.info(f"Ожидаем загрузки DOM страницы {timeout}s  при времени неактивности {inactivity_timeout}s")
        start_time = time.time()
        last_activity = time.time()
        active_frames = set()
        target_elements_found = False

        while True:
            now = time.time()

            if now - start_time > timeout:
                self.log.warning("Таймаут истек во время ожидания загрузки DOM")
                break

            if now - last_activity > inactivity_timeout:
                self.log.info("Таймаут неактивности истек во время ожидания загрузки DOM")
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

                self.log.debug(f"Получили сообщение: {method}")

                if method == "DOM.attributeModified":
                    frame_id = params.get("nodeId")
                    if frame_id:
                        active_frames.add(frame_id)
                        self.log.debug(f"Node {frame_id} attribute modified")

                elif method == "Page.frameStoppedLoading":
                    frame_id = params.get("frameId")
                    if frame_id in active_frames:
                        active_frames.remove(frame_id)
                        self.log.debug(f"Frame {frame_id} stopped loading")

                elif method == "Page.frameDetached":
                    frame_id = params.get("frameId")
                    if frame_id in active_frames:
                        active_frames.remove(frame_id)
                        self.log.debug(f"Frame {frame_id} detached")

                elif method == "Page.loadEventFired":
                    self.log.info("Закончилась загрузка главного фрейма")

                elif method == "DOM.documentUpdated":
                    try:
                        search_result = await self.perform_search(f"//*[contains(@class, '{target_class}')]")
                        if search_result and search_result.get("resultCount", 0) > 0:
                            target_elements_found = True
                            self.log.info(f"Нашлось {search_result['resultCount']} целевых элементов после загрузки DOM")
                    except Exception as e:
                        self.log.error(f"Ошибка поиска после обновления DOM: {e}")
                elif method == "DOM.inlineStyleInvalidated":
                    continue


            except Exception as e:
                self.log.error(f"Не удалось обработать CDP сообщение: {e}")

        self.log.info("Загрузка страницы и стабильность DOM проверены")

    async def get_document(self, depth: int = 2) -> Dict:
        """Получить корневой элемент документа."""
        response = await self.send_request("DOM.getDocument", {"depth": depth})
        parsed = await parse_response(response)
        self.log.debug(f"Получен документ: {parsed}")
        return parsed

    async def query_selector(self, root_node_id: int, selector: str) -> Optional[int]:
        query_response = await self.send_request("DOM.querySelector", {
            "nodeId": root_node_id,
            "selector": selector
        })
        parsed_query = await parse_response(query_response)

        while parsed_query.get("result", {}).get("nodeId") is None:
            query_response = await self.client.receive_message()
            parsed_query = await parse_response(query_response)
            if parsed_query.get("result", {}).get("nodeId") is not None:
                break

        node_id = parsed_query.get("result", {}).get("nodeId")
        if not node_id:
            self.log.error(f"Элемент с локатором '{selector}' не найден")
            return None
        return node_id

    async def highlight_element_border(self, node_id: int,
                                       color: str = "red",
                                       thickness: str = "2px",
                                       duration: float = 15.0) -> bool:
        """
        Добавляет визуальную рамку к элементу по nodeId через RuntimeHandler.
        """
        try:
            resolved = await self._runtime.resolve_node(node_id, object_group="highlight")
            object_id = resolved.get("result", {}).get("object", {}).get("objectId")
            if not object_id:
                self.log.error("Не можем найти objectId у элемента")
                return False

            function_declaration = f"""
                function() {{
                    if (!this || !this.style) return false;
                    const original = this.style.border;
                    this.style.border = '{thickness} solid {color}';
                    setTimeout(() => {{ this.style.border = original; }}, {int(duration * 1000)});
                    return true;
                }}
            """
            response = await self._runtime.call_function_on(object_id, function_declaration)
            success = response.get("result", {}).get("value")
            await asyncio.sleep(0.5)
            self.log.info(f"Успешно загрузили подсветку: {success}")
            return success is True
        except Exception as e:
            self.log.error(f"Подсветка завершена неудачно: {e}")
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
            parsed_search = await parse_response(search_response)

            search_id = parsed_search.get("searchId") or parsed_search.get("result", {}).get("searchId")
            # logger_odj.error(search_id)
            result_count = parsed_search.get("resultCount") or parsed_search.get("result", {}).get("resultCount", 0)

            if not search_id:
                self.log.error("Нет searchId в ответе")
                return None

            if result_count == 0:
                self.log.debug("Элементы не найдены")
                return None

        finally:
            self.log.info(f"Нашлось {result_count} элементов с searchId = {search_id}, ")

        return search_id

    async def get_root_node_id(self):
        document = await self.get_document()
        root_node_id = document.get("result", {}).get("root", {}).get("nodeId")
        if not root_node_id:
            self.log.error("Ошибка получения корневого node ID")
            return None
        return root_node_id

    async def describe_node(self, node_id):
        node_info = await self.send_request("DOM.describeNode", {"nodeId": node_id})
        parsed_node_info = await parse_response(node_info)
        parsed_node_info.get("result", {}).get("node")
        return parsed_node_info

    async def get_box_model(self, node_id: int) -> Optional[Dict]:
        """Получить модель Box для элемента."""
        response = await self.send_request("DOM.getBoxModel", {"nodeId": node_id})
        parsed = await parse_response(response)
        return parsed.get("result", {}).get("model")

    async def get_search_results(self, search_id):
        try:
            params = {
                "searchId": search_id,
                "fromIndex": 0,
                "toIndex": 1
            }
            search_response = await self.send_request("DOM.getSearchResults", params)
            parsed_query = await parse_response(search_response)
            while parsed_query.get("result", {}).get("nodeIds") is None:
                query_response = await self.client.receive_message()
                parsed_query = await parse_response(query_response)
                if parsed_query.get("result", {}).get("nodeIds") is not None:
                    break

            node_id = parsed_query.get("result", {}).get("nodeIds")[0]
            return node_id


        except Exception as e:
            self.log.error(f"Ошибка поиска элемента по search ID: {e}")
            return None

    async def find_element_by_xpath(self, xpath: str) -> Element | None:
        """
        Найти элемент по XPath и вернуть объект Element.
        Логирует все действия в StepLogger, который создаётся автоматически, если не передан.

        :param xpath: XPath-выражение
        :return: Element или None
        """
        try:

            document = await self.get_document()
            search_id = await self.perform_search(xpath)
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
                dom_handler=self,
                input_handler=InputHandler(self.client, self.log),
                logger = self.log
            )

            return element

        except Exception as e:
            self.log.error(f"Ошибка поиска элемента по XPath: {e}")
            return None

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
            parsed = await parse_response(response)
            return parsed.get("result", {}).get("outerHTML")
        except Exception as e:
            self.log.error(f"Ошибка получения outerHTML: {e}")
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
            parsed = await parse_response(response)
            return parsed.get("result", {}).get("innerHTML")
        except Exception as e:
            self.log.error(f"Ошибка получения innerHTML: {e}")
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
                self.log.error("Не получены данные об элементе")
                return False

            node_id = element_data.get("nodeId")
            if not node_id:
                self.log.error("У элемента нет nodeId")
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

            parsed = await parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value")
        except Exception as e:
            self.log.error(f"Ошибка получения текста элемента: {e}")
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

            parsed = await parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value")
        except Exception as e:
            self.log.error(f"Ошибка получения текста элемента: {e}")
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
            parsed = await parse_response(response)
            attributes = parsed.get("result", {}).get("attributes", [])

            # Преобразуем список [name1, value1, name2, value2, ...] в словарь
            return dict(zip(attributes[::2], attributes[1::2]))
        except Exception as e:
            self.log.error(f"Ошибка получения атрибутов элемента: {e}")
            return None

    async def is_alert_open(self) -> bool:
        try:
            # Отправляем запрос на закрытие диалога
            response = await self.send_request("Page.handleJavaScriptDialog", {
                "accept": True
            })

            await self.client.receive_message()
            await self.client.receive_message()
            pa = PageHandler(self.client, self.log)
            await pa.wait_for_page_dom_load(5, 2)
            return True  # Алерт был и мы его обработали

        except Exception as e:
            if "No dialog is showing" in str(e):
                return False
            self.log.error(f"Ошибка проверки алерта: {e}")
            return False

    async def is_element_visible(self, node_id: int) -> bool:
        """
        Проверяет, видим ли элемент (display, visibility, opacity) через RuntimeHandler.
        :param node_id: Идентификатор DOM-узла
        :return: True, если элемент видим
        """
        self.log.info(f"Проверяем видимость элемента {node_id}")
        try:
            resolved = await self._runtime.resolve_node(node_id)
            object_id = resolved.get("result", {}).get("object", {}).get("objectId")
            if not object_id:
                self.log.error("Не получилось узнать objectId для проверки видимости")
                return False

            js_declaration = (
                "function() {"
                " try {"
                " const style = window.getComputedStyle(this);"
                " return style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity) > 0;"
                " } catch (e) { return false; }"
                "}"
            )
            response = await self._runtime.call_function_on(object_id, js_declaration)
            value = response.get("result", {}).get("result", {}).get("value")
            return value is True
        except Exception as e:
            self.log.error(f"Ошибка проверки видимости элемента: {e}")
            return False

    async def is_element_clickable(self, node_id: int) -> bool:
        """
        Проверяет, кликабелен ли элемент (видим, не заблокирован, имеет размеры) через RuntimeHandler.
        :param node_id: Идентификатор DOM-узла
        :return: True, если элемент кликабелен
        """
        self.log.info(f"Проверяем кликабельность элемента {node_id}")
        try:
            resolved = await self._runtime.resolve_node(node_id)
            object_id = resolved.get("result", {}).get("object", {}).get("objectId")
            if not object_id:
                self.log.error("Не получилось узнать objectId для проверки кликабельности")
                return False

            js_declaration = (
                "function() {"
                " try {"
                " const style = window.getComputedStyle(this);"
                " const rect = this.getBoundingClientRect();"
                " return style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity) > 0 && !this.disabled && rect.width > 0 && rect.height > 0;"
                " } catch (e) { return false; }"
                "}"
            )
            response = await self._runtime.call_function_on(object_id, js_declaration)
            value = response.get("result", {}).get("result", {}).get("value")
            return value is True
        except Exception as e:
            self.log.error(f"Ошибка проверки кликабельности элемента: {e}")
            return False
