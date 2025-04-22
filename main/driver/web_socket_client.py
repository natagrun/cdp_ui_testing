import asyncio
from typing import Any
import aiohttp
import websockets
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

async def get_websocket_url() -> Any | None:
    """
    Получить WebSocket URL первой открытой страницы из DevTools.

    :return: Строка с WebSocket URL или None в случае ошибки
    """
    devtools_url = "http://localhost:9222/json"
    logger.info("Попытка получения WebSocket URL из DevTools")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(devtools_url) as response:
                logger.debug(f"Ответ DevTools: статус {response.status}")

                if response.status != 200:
                    logger.error("Не удалось получить список страниц из DevTools")
                    return None

                pages = await response.json()

                if not pages:
                    logger.warning("DevTools не вернул ни одной страницы")
                    return None

                first_page = pages[0]
                url = first_page.get("webSocketDebuggerUrl", "")

                if not url:
                    logger.warning("URL WebSocket отсутствует в ответе DevTools")
                    return None

                logger.info(f"Выбран WebSocket URL: {url}")
                return url

    except Exception as e:
        logger.error(f"Ошибка при получении WebSocket URL: {e}")
        return None


class WebSocketClient:
    """
    Класс для работы с WebSocket-соединением.
    """

    def __init__(self, url: str = None):
        """
        Инициализация клиента WebSocket.

        :param url: Адрес WebSocket-соединения
        """
        self.url = url
        self.websocket = None
        logger.debug(f"Создан экземпляр WebSocketClient с URL: {url}")

    async def connect(self, retries: int = 3):
        """
        Установить соединение с WebSocket с повтором при ошибке.

        :param retries: Количество попыток
        :raises ConnectionError: Если соединение не удалось после всех попыток
        """
        logger.info(f"Подключение к WebSocket с количеством попыток: {retries}")
        for attempt in range(1, retries + 1):
            try:
                self.websocket = await websockets.connect(self.url)
                logger.info("Соединение с WebSocket установлено")
                return
            except Exception as e:
                logger.warning(f"Попытка {attempt} подключения к WebSocket не удалась: {e}")
                await asyncio.sleep(1)

        logger.error("Не удалось установить соединение с WebSocket после всех попыток")
        raise ConnectionError("Не удалось подключиться к WebSocket")

    async def send_message(self, message: str):
        """
        Отправка сообщения по WebSocket.

        :param message: Строка с сообщением
        """
        if self.websocket:
            logger.debug(f"Отправка сообщения: {message}")
            # print(message)
            await self.websocket.send(message)
        else:
            logger.error("Невозможно отправить сообщение — WebSocket не подключён")

    async def receive_message(self):
        """
        Получение сообщения из WebSocket.

        :return: Строка с полученным сообщением или None при ошибке
        """
        try:
            message = await self.websocket.recv()
            logger.debug(f"Получено сообщение из WebSocket: {message}")
            # print(message)
            return message
        except Exception as e:
            logger.error(f"Ошибка при получении сообщения из WebSocket: {e}")
            return None

    async def close(self):
        """
        Закрытие WebSocket-соединения.
        """
        if self.websocket:
            await self.websocket.close()
            logger.info("Соединение WebSocket закрыто")
        else:
            logger.warning("Попытка закрытия WebSocket, но соединение не установлено")
