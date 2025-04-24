import json
import logging
from typing import Optional, List

from main.driver.web_socket_client import WebSocketClient
from main.handlers.base_handler import BaseHandler
from main.handlers.page_handler import PageHandler
from main.utils.parser import parse_response

logger = logging.getLogger(__name__)


class NavigationHandler(BaseHandler):
    def __init__(self, websocket_client: WebSocketClient):
        super().__init__(websocket_client)
        self.current_index = None

    async def get_navigation_history(self) -> Optional[List[dict]]:
        try:
            response = await self.send_request("Page.getNavigationHistory")
            parsed = await parse_response(response)
            entries = parsed.get("result", {}).get("entries", [])
            self.current_index = parsed.get("result", {}).get("currentIndex", -1)
            logger.info(f"Найдено {len(entries)} записей в истории навигации.")
            return entries
        except Exception as e:
            logger.error(f"Ошибка при получении истории навигации: {e}")
            return None

    async def get_current_url(self):
        entries = await self.get_navigation_history()
        return entries[-1].get("url") if entries else None

    async def navigate_back(self) -> bool:
        try:
            history = await self.get_navigation_history()
            if history is None:
                return False
            page = PageHandler(self.client)
            if self.current_index > 0:
                entry_id = history[self.current_index - 1]["id"]
                await self.send_request("Page.navigateToHistoryEntry", {"entryId": entry_id})
                logger.info("Переход назад по истории навигации.")
                await page.wait_for_page_load()
                return True
            else:
                logger.warning("Нет предыдущей записи в истории.")
                return False
        except Exception as e:
            logger.error(f"Ошибка при переходе назад: {e}")
            return False

    async def navigate_forward(self) -> bool:
        try:
            history = await self.get_navigation_history()
            if history is None:
                return False
            page = PageHandler(self.client)
            if self.current_index < len(history) - 1:
                entry_id = history[self.current_index + 1]["id"]
                await self.send_request("Page.navigateToHistoryEntry", {"entryId": entry_id})
                logger.info("Переход вперёд по истории навигации.")
                await page.wait_for_page_load()
                return True
            else:
                logger.warning("Нет следующей записи в истории.")
                return False
        except Exception as e:
            logger.error(f"Ошибка при переходе вперёд: {e}")
            return False

    async def switch_to_iframe(self, node_id: int) -> Optional[str]:
        try:
            described = await self.send_request("DOM.describeNode", {"nodeId": node_id})
            frame_id = described.get("result", {}).get("node", {}).get("frameId")
            if not frame_id:
                logger.warning("Не найден frameId для указанного узла.")
                return None
            await self.send_request("Page.setLifecycleEventsEnabled", {"enabled": True})
            await self.send_request("Runtime.evaluate", {
                "expression": "window.frameElement.contentWindow.focus()"
            })
            logger.info(f"Переключено на iframe с frameId: {frame_id}")
            return frame_id
        except Exception as e:
            logger.error(f"Ошибка при переключении на iframe: {e}")
            return None

    async def switch_to_main_frame(self) -> bool:
        try:
            await self.send_request("Page.navigate", {"url": "javascript:window.top.focus();"})
            logger.info("Возврат в основной фрейм.")
            return True
        except Exception as e:
            logger.error(f"Ошибка при возврате в основной фрейм: {e}")
            return False

    async def handle_new_tabs_and_windows(self):
        try:
            await self.send_request("Target.setDiscoverTargets", {"discover": True})
            logger.info("Отслеживание новых вкладок и окон активировано.")
            while True:
                message = await self.client.receive_message()
                data = json.loads(message)
                if data.get("method") == "Target.targetCreated":
                    target_info = data["params"]["targetInfo"]
                    logger.info(f"Обнаружена новая вкладка/окно: {target_info['url']} (ID: {target_info['targetId']})")
                elif data.get("method") == "Target.targetDestroyed":
                    logger.info(f"Закрыта вкладка/окно с ID: {data['params']['targetId']}")
        except Exception as e:
            logger.error(f"Ошибка при отслеживании вкладок и окон: {e}")

    async def close_browser(self):
        try:
            await self.send_request("Browser.close")
            logger.info("Браузер закрыт.")
        except Exception as e:
            logger.error(f"Ошибка при закрытии браузера: {e}")