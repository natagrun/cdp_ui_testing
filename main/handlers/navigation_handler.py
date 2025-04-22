import json
import logging

from main.driver.web_socket_client import WebSocketClient
from main.handlers.page_handler import PageHandler
from main.utils.parser import parse_response

logger = logging.getLogger(__name__)
from typing import Optional, List

from main.handlers.base_handler import BaseHandler


class NavigationHandler(BaseHandler):
    def __init__(self, websocket_client: WebSocketClient):
        super().__init__(websocket_client)
        self.current_index = None

    async def get_navigation_history(self) -> Optional[List[dict]]:
        """Получить список истории навигации страницы."""
        try:
            response = await self.send_request("Page.getNavigationHistory")
            parsed= await parse_response(response)
            entries = parsed.get("result", {}).get("entries", [])
            self.current_index = parsed.get("result", {}).get("currentIndex", -1)
            logger.info(f"Found {len(entries)} entries in navigation history.")
            return entries
        except Exception as e:
            logger.error(f"Failed to get navigation history: {e}")
            return None

    async def get_current_url(self):
        """Возвращает текущий URL страницы."""
        entrues = await self.get_navigation_history()
        return entrues[-1].get("url")

    async def navigate_back(self) -> bool:
        """Переход на предыдущую страницу в истории."""
        try:
            history = await self.get_navigation_history()
            if history is None:
                return False
            page = PageHandler(self.client)
            if self.current_index > 0:
                entry_id = history[self.current_index - 1]["id"]
                await self.send_request("Page.navigateToHistoryEntry", {"entryId": entry_id})
                logger.info("Navigated back in history.")
                await page.wait_for_page_load()
                return True
            else:
                logger.warning("No previous entry in history.")
                return False
        except Exception as e:
            logger.error(f"Failed to navigate back: {e}")
            return False

    async def navigate_forward(self) -> bool:
        """Переход вперёд в истории страницы."""
        try:
            history = await self.get_navigation_history()
            if history is None:
                return False
            page = PageHandler(self.client)
            if self.current_index < len(history) - 1:
                entry_id = history[self.current_index + 1]["id"]
                await self.send_request("Page.navigateToHistoryEntry", {"entryId": entry_id})
                logger.info("Navigated forward in history.")
                await page.wait_for_page_load()
                return True
            else:
                logger.warning("No next entry in history.")
                return False
        except Exception as e:
            logger.error(f"Failed to navigate forward: {e}")
            return False

    async def switch_to_iframe(self, node_id: int) -> Optional[str]:
        """Переключиться на iframe по nodeId и вернуть frameId."""
        try:
            described = await self.send_request("DOM.describeNode", {"nodeId": node_id})
            frame_id = described.get("result", {}).get("node", {}).get("frameId")
            if not frame_id:
                logger.warning("No frameId found for given node.")
                return None

            await self.send_request("Page.setLifecycleEventsEnabled", {"enabled": True})
            await self.send_request("Runtime.evaluate", {
                "expression": f"window.frameElement.contentWindow.focus()"
            })
            logger.info(f"Switched to iframe with frameId: {frame_id}")
            return frame_id
        except Exception as e:
            logger.error(f"Failed to switch to iframe: {e}")
            return None

    async def switch_to_main_frame(self) -> bool:
        """Возврат в основной фрейм (main frame)."""
        try:
            await self.send_request("Page.navigate", {"url": "javascript:window.top.focus();"})
            logger.info("Switched to main frame.")
            return True
        except Exception as e:
            logger.error(f"Failed to switch to main frame: {e}")
            return False