import json
import logging
from typing import Union, Dict
import json
import logging
from typing import Union, Dict

from main.driver.web_socket_client import WebSocketClient  # подключаем обновлённый WebSocketClient

logger = logging.getLogger(__name__)


def parse_response(response: Union[str, Dict]) -> Dict:
    """Парсит ответ CDP (может быть строкой JSON или уже словарём)."""
    if isinstance(response, str):
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CDP response: {e}")
            return {}
    return response


class BaseHandler:
    """Общий класс для обработки запросов с инкрементированием ID."""

    def __init__(self, websocket_client: WebSocketClient):
        self.client = websocket_client
        self.request_id = 1

    def get_next_id(self) -> int:
        current_id = self.request_id
        self.request_id += 1
        return current_id

    async def send_request(self, method: str, params: dict = None) -> Dict:
        """Отправить запрос в WebSocket и получить распарсенный ответ."""
        request_id = self.get_next_id()
        command = {
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        command_json = json.dumps(command)
        logger.debug(f"Sending CDP command: {command_json}")
        await self.client.send_message(command_json)
        return await self.receive_and_parse()

    async def receive_and_parse(self) -> Dict:
        """Получить сообщение и сразу его распарсить."""
        response = await self.client.receive_message()
        return parse_response(response)
