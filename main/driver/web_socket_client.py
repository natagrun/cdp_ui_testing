import asyncio
import logging
from typing import *

import websockets

class WebSocketClient:
    """
    Класс для работы с WebSocket-соединением.
    """
    def __init__(self, url: str, connect_timeout: int, retries: int, logger):
        self.url = url
        self.websocket = None
        self.retries = retries
        self.connect_timeout = connect_timeout
        self.log = logger
        self.log.debug(f"Создан WebSocketClient(url={url}, retries={retries}, timeout={connect_timeout})")

    async def connect(self) -> None:
        self.log.info(f"Подключение к WebSocket {self.url} (попыток: {self.retries})")
        for attempt in range(1, self.retries + 1):
            try:
                self.websocket = await websockets.connect(self.url, timeout=self.connect_timeout)
                self.log.info("Соединение с WebSocket установлено")
                return
            except Exception as e:
                self.log.warning(f"Попытка {attempt} не удалась: {e}")
                await asyncio.sleep(1)
        self.log.error("Не удалось подключиться к WebSocket после всех попыток")
        raise ConnectionError("WebSocket connect failed")

    async def send_message(self, message: str) -> None:
        if self.websocket:
            self.log.debug(f"Отправка сообщения: {message}")
            await self.websocket.send(message)
        else:
            self.log.error("WebSocket не подключён, отправка невозможна")

    async def receive_message(self) -> Optional[str]:
        try:
            message = await self.websocket.recv()
            self.log.debug(f"Получено сообщение: {message}")
            return message
        except Exception as e:
            self.log.error(f"Ошибка при получении: {e}")
            return None

    async def close(self) -> None:
        if self.websocket:
            await self.websocket.close()
            self.log.info("WebSocket соединение закрыто")

