import asyncio
import websockets
import json
import aiohttp
import base64

from main.driver.web_socket_client import WebSocketClient


class BaseHandler:
    """Общий класс для обработки запросов с инкрементированием ID."""

    def __init__(self, websocket_client: 'WebSocketClient'):
        self.client = websocket_client
        self.request_id = 1  # Начальный ID для запроса

    def get_next_id(self) -> int:
        """Возвращает следующий ID для запроса."""
        current_id = self.request_id
        self.request_id += 1
        return current_id

    async def send_request(self, method: str, params: dict = None) -> str:
        """Отправить запрос в WebSocket и получить ответ."""
        request_id = self.get_next_id()
        command = {
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        command_json = json.dumps(command)
        print(command_json)
        await self.client.send_message(command_json)

        # Получаем ответ от WebSocket
        response = await self.client.receive_message()
        return response
