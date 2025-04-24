import asyncio
import logging
import time
from typing import Optional

from main.driver.web_socket_client import WebSocketClient
from main.handlers.dom_handler import DOMHandler
from main.handlers.page_handler import PageHandler
from main.driver.web_socket_client import get_websocket_url

logger = logging.getLogger(__name__)


class CdpDriver:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CdpDriver, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "initialized") and self.initialized:
            return

        self.websocket_client: Optional[WebSocketClient] = None
        self.page: Optional[PageHandler] = None
        self.dom: Optional[DOMHandler] = None
        self.initialized = False

    async def setup(self):
        logger.info("Инициализация драйвера...")
        url = await get_websocket_url()
        if not url:
            logger.error("Не удалось получить WebSocket URL. Завершение работы.")
            return False

        self.websocket_client = WebSocketClient(url)
        try:
            await self.websocket_client.connect()
        except Exception as e:
            logger.error(f"Ошибка подключения к WebSocket: {e}")
            return False

        self.page = PageHandler(self.websocket_client)
        self.dom = DOMHandler(self.websocket_client)

        try:
            await self.page.enable_page()
            await self.dom.enable_dom()
        except Exception as e:
            logger.error(f"Ошибка при активации доменов CDP: {e}")
            await self.teardown()
            return False

        self.initialized = True
        logger.info("Драйвер успешно инициализирован.")
        return True

    async def teardown(self):
        logger.info("Завершение работы драйвера...")
        try:
            if self.websocket_client:
                await self.websocket_client.close()
        except Exception as e:
            logger.warning(f"Ошибка при закрытии WebSocket: {e}")
        finally:
            self.websocket_client = None
            self.page = None
            self.dom = None
            self.initialized = False
            CdpDriver._instance = None
        logger.info("Ресурсы драйвера освобождены.")
