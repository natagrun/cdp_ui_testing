import asyncio
from typing import Any

import aiohttp
import websockets
import logging

logger = logging.getLogger(__name__)


async def get_websocket_url() -> Any | None:
    """Получить WebSocket URL первой открытой страницы из DevTools."""
    devtools_url = "http://localhost:9222/json"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(devtools_url) as response:
                if response.status != 200:
                    logger.error("Failed to retrieve pages list from DevTools")
                    return None

                pages = await response.json()

                if not pages:
                    logger.warning("No pages found on DevTools")
                    return None

                first_page = pages[0]
                url = first_page.get("webSocketDebuggerUrl", "")
                logger.info(f"Selected WebSocket URL: {url}")
                return url

    except Exception as e:
        logger.error(f"Error fetching WebSocket URL: {e}")
        return None


class WebSocketClient:
    """Класс для работы с WebSocket-соединением."""

    def __init__(self, url: str = None):
        self.url = url
        self.websocket = None

    async def connect(self, retries: int = 3):
        """Подключаемся к WebSocket с попытками повтора."""
        for attempt in range(retries):
            try:
                self.websocket = await websockets.connect(self.url)
                logger.info("WebSocket connection established!")
                return
            except Exception as e:
                logger.warning(f"WebSocket connection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)

        raise ConnectionError("Unable to establish WebSocket connection after retries")

    async def send_message(self, message: str):
        """Отправить сообщение в WebSocket."""
        if self.websocket:
            await self.websocket.send(message)
            print(message)
        else:
            logger.error("WebSocket not connected")

    async def receive_message(self):
        """Получить ответ из WebSocket."""
        try:
            message = await self.websocket.recv()
            logger.debug(f"Received WebSocket message: {message}")
            print(message)
            return message
        except Exception as e:
            logger.error(f"Error receiving WebSocket message: {e}")
            return None

    async def close(self):
        """Закрыть WebSocket-соединение."""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")

