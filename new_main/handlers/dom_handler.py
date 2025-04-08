import asyncio
import json
from typing import Optional, Dict, List, Union
import logging

from new_main.handlers.base_handler import BaseHandler

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


    async def query_selector(self, node_id: int, selector: str) -> Optional[int]:
        """Найти элемент по CSS-селектору."""
        response = await self.send_request("DOM.querySelector", {
            "nodeId": node_id,
            "selector": selector
        })
        parsed = await _parse_response(response)
        return parsed.get("result", {}).get("nodeId")

    async def query_selector_xpath(self, xpath: str, node_id: Optional[int] = None) -> Optional[int]:
        """Найти первый элемент по XPath."""
        try:
            params = {
                "query": xpath,
                "includeUserAgentShadowDOM": True
            }
            if node_id is not None:
                params["nodeId"] = node_id

            # Шаг 1: Выполняем поиск
            search_response = await self.send_request("DOM.performSearch", params)
            parsed_search = await _parse_response(search_response)

            search_id = parsed_search.get("searchId") or parsed_search.get("result", {}).get("searchId")
            result_count = parsed_search.get("resultCount") or parsed_search.get("result", {}).get("resultCount", 0)

            if not search_id:
                logger.error("No searchId in response")
                return None

            if result_count == 0:
                logger.debug("No elements found")
                return None

            # Шаг 2: Получаем результаты (только если есть элементы)
            results_response = await self.send_request("DOM.getSearchResults", {
                "searchId": search_id,
                "fromIndex": 0,
                "toIndex": 1  # Запрашиваем только первый элемент
            })
            parsed_results = await _parse_response(results_response)
            # print(parsed_results)
            # Обрабатываем возможные форматы ответа
            if isinstance(parsed_results, dict):
                if "error" in parsed_results:
                    logger.error(f"CDP error: {parsed_results['error']}")
                    return None

                node_ids = parsed_results.get("nodeIds") or parsed_results.get("result", {}).get("nodeIds", [])
                return node_ids[0] if node_ids else None

            return None

        except Exception as e:
            logger.error(f"XPath search error: {e}")
            return None

    async def find_element_by_id(self, element_id: str) -> Optional[Dict]:
        """
        Найти элемент по ID и вернуть его данные.
        Возвращает словарь с nodeId, backendNodeId и другими данными элемента, или None если не найден.
        """
        try:
            # 1. Получаем корневой документ
            document = await self.get_document()
            root_node_id = document.get("result", {}).get("root", {}).get("nodeId")
            if not root_node_id:
                logger.error("Failed to get root node ID")
                return None

            # 2. Ищем элемент по ID через querySelector
            query_response = await self.send_request("DOM.querySelector", {
                "nodeId": root_node_id,
                "selector": f"#{element_id}"
            })
            parsed_query = await _parse_response(query_response)

            # Ожидаем ответа с nodeId
            while parsed_query.get("result", {}).get("nodeId") is None:
                query_response = await self.client.receive_message()
                parsed_query = await _parse_response(query_response)
                if parsed_query.get("result", {}).get("nodeId") is not None:
                    break

            node_id = parsed_query.get("result", {}).get("nodeId")
            if not node_id:
                logger.error(f"Element with id '{element_id}' not found")
                return None

            # 3. Получаем полную информацию о ноде
            node_info = await self.send_request("DOM.describeNode", {"nodeId": node_id})
            parsed_node_info = await _parse_response(node_info)

            # 4. Получаем координаты элемента
            box_model = await self.send_request("DOM.getBoxModel", {"nodeId": node_id})
            parsed_box_model = await _parse_response(box_model)

            if not all([
                parsed_node_info.get("result", {}).get("node"),
                parsed_box_model.get("result", {}).get("model")
            ]):
                logger.error("Failed to get complete element info")
                return None

            return {
                "nodeId": node_id,
                "backendNodeId": parsed_node_info["result"]["node"].get("backendNodeId"),
                "nodeName": parsed_node_info["result"]["node"].get("nodeName"),
                "boxModel": parsed_box_model["result"]["model"],
                "documentURL": document.get("result", {}).get("documentURL")
            }

        except Exception as e:
            logger.error(f"Error finding element by ID: {e}")
            return None

    async def click_element(self, element_data: Dict) -> bool:
        """
        Кликнуть на элемент с использованием Input.dispatchMouseEvent.
        element_data - данные элемента, полученные из find_element_by_id.
        Возвращает True, если клик выполнен успешно, иначе False.
        """
        try:
            if not element_data:
                logger.error("No element data provided")
                return False

            # 1. Активируем Input domain если еще не активирован
            await self.send_request("Input.enable", {})

            # 2. Получаем координаты центра элемента
            model = element_data.get("boxModel")
            if not model:
                logger.error("No box model data")
                return False

            # Координаты центра элемента
            x = (model["content"][0] + model["content"][2]) / 2
            y = (model["content"][1] + model["content"][5]) / 2

            # 3. Последовательность событий для клика
            # a. Наведение мыши
            await self.send_request("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": x,
                "y": y,
                "modifiers": 0,
                "button": "none",
                "buttons": 0
            })

            # b. Нажатие кнопки мыши
            await self.send_request("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "modifiers": 0,
                "button": "left",
                "buttons": 1,
                "clickCount": 1
            })

            # c. Отпускание кнопки мыши
            await self.send_request("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "modifiers": 0,
                "button": "left",
                "buttons": 0,
                "clickCount": 1
            })

            logger.debug(f"Successfully clicked element at ({x}, {y})")
            return True

        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False

    async def click_element_by_id(self, element_id: str) -> bool:
        """
        Комбинированная функция: найти элемент по ID и кликнуть на него.
        Возвращает True, если клик выполнен успешно, иначе False.
        """
        element_data = await self.find_element_by_id(element_id)
        if not element_data:
            return False

        return await self.click_element(element_data)

    async def click_element_by_xpath(self, xpath: str) -> bool:
        """Альтернативная реализация через XPath с учетом особенностей CDP"""
        try:
            # 1. Получаем корневой документ
            document = await self.get_document()
            root_node_id = document.get("result", {}).get("root", {}).get("nodeId")
            if not root_node_id:
                logger.error("Failed to get root node ID")
                return False

            # 2. Выполняем поиск
            search_response = await self.send_request("DOM.performSearch", {
                "query": xpath,
                "includeUserAgentShadowDOM": True,
                "nodeId": root_node_id
            })
            parsed_search = await _parse_response(search_response)
            search_id = parsed_search.get("result", {}).get("searchId")

            if not search_id:
                logger.error("Search failed, no searchId returned")
                return False

            # 3. Получаем результаты
            results_response = await self.send_request("DOM.getSearchResults", {
                "searchId": search_id,
                "fromIndex": 0,
                "toIndex": 1
            })
            parsed_results = await _parse_response(results_response)
            node_ids = parsed_results.get("result", {}).get("nodeIds", [])

            if not node_ids:
                logger.error("No nodeIds in search results")
                return False

            # 4. Для первого найденного элемента
            node_id = node_ids[0]

            # 5. Получаем backendNodeId
            node_info = await self.send_request("DOM.describeNode", {"nodeId": node_id})
            parsed_node_info = await _parse_response(node_info)
            backend_node_id = parsed_node_info.get("result", {}).get("node", {}).get("backendNodeId")

            if not backend_node_id:
                logger.error("Failed to get backendNodeId")
                return False

            # 6. Разрешаем ноду и кликаем (как в предыдущем примере)
            resolve_response = await self.send_request("DOM.resolveNode", {
                "backendNodeId": backend_node_id
            })
            parsed_resolve = await _parse_response(resolve_response)
            object_id = parsed_resolve.get("result", {}).get("object", {}).get("objectId")

            if not object_id:
                logger.error("Failed to get objectId")
                return False

            click_response = await self.send_request("Runtime.callFunctionOn", {
                "objectId": object_id,
                "functionDeclaration": "function() { this.click(); }",
                "returnByValue": True
            })
            parsed_click = await _parse_response(click_response)

            if "error" in parsed_click:
                logger.error(f"Click failed: {parsed_click['error']}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error clicking element by XPath: {e}")
            return False


    async def query_selector_all_xpath(self, xpath: str, node_id: Optional[int] = None) -> List[int]:
        """Найти все элементы по XPath."""
        try:
            params = {
                "query": xpath,
                "includeUserAgentShadowDOM": True
            }
            if node_id is not None:
                params["nodeId"] = node_id

            # Шаг 1: Выполняем поиск
            search_response = await self.send_request("DOM.performSearch", params)
            parsed_search = await _parse_response(search_response)

            search_id = (parsed_search.get("searchId") or
                         parsed_search.get("result", {}).get("searchId"))
            total_results = (parsed_search.get("resultCount") or
                             parsed_search.get("result", {}).get("resultCount", 0))

            if not search_id or total_results == 0:
                return []

            # Шаг 2: Получаем все результаты
            results_response = await self.send_request("DOM.getSearchResults", {
                "searchId": search_id,
                "fromIndex": 0,
                "toIndex": total_results
            })
            parsed_results = await _parse_response(results_response)

            return (parsed_results.get("nodeIds") or
                    parsed_results.get("result", {}).get("nodeIds", []))

        except Exception as e:
            logger.error(f"XPath search error: {e}")
            return []

    async def get_attributes(self, node_id: int) -> Dict[str, str]:
        """Получить все атрибуты элемента."""
        response = await self.send_request("DOM.getAttributes", {"nodeId": node_id})
        parsed = await _parse_response(response)
        attrs = parsed.get("result", {}).get("attributes", [])
        return dict(zip(attrs[::2], attrs[1::2]))

    async def get_node_info(self, node_id: int) -> Dict:
        """Получить информацию об узле."""
        response = await self.send_request("DOM.describeNode", {"nodeId": node_id})
        return await _parse_response(response)

    async def get_box_model(self, node_id: int) -> Optional[Dict]:
        """Получить модель Box для элемента."""
        response = await self.send_request("DOM.getBoxModel", {"nodeId": node_id})
        parsed = await _parse_response(response)
        return parsed.get("result", {}).get("model")