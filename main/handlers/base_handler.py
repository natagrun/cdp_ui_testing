import json
import logging

from main.driver.web_socket_client import WebSocketClient  # подключаем обновлённый WebSocketClient

logger = logging.getLogger(__name__)


class BaseHandler:
    """
    Базовый класс для отправки команд Chrome DevTools Protocol (CDP)
    через WebSocket-клиент с автоинкрементом идентификаторов запросов.
    """

    def __init__(self, websocket_client: WebSocketClient):
        """
        Инициализирует объект BaseHandler с привязанным WebSocket-клиентом.

        :param websocket_client: Объект WebSocketClient для связи с CDP
        """

        self.client = websocket_client
        self.request_id = 1

    def get_next_id(self) -> int:
        """
        Получает следующий уникальный идентификатор запроса.

        :return: Целое число — ID запроса
        """
        current_id = self.request_id
        self.request_id += 1
        return current_id

    async def send_request(self, method: str, params: dict = None):
        """
        Отправляет команду CDP через WebSocket и возвращает ответ.

        :param method: Строка с именем команды CDP (например, "DOM.getDocument")
        :param params: Словарь с параметрами команды (по умолчанию пустой)
        :return: Ответ от CDP в виде словаря
        """
        request_id = self.get_next_id()
        command = {
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        command_json = json.dumps(command)
        logger.debug(f"Sending CDP command: {command_json}")
        await self.client.send_message(command_json)
        return await self.client.receive_message()