import asyncio
import websockets
import json
import aiohttp
import base64

class WebSocketClient:
    """Класс для работы с WebSocket-соединением."""

    def __init__(self, url: str = None):
        self.url = url
        self.websocket = None

    async def connect(self):
        """Подключаемся к WebSocket."""
        self.websocket = await websockets.connect(self.url)
        print("WebSocket connection established!")

    async def send_message(self, message: str):
        """Отправить сообщение в WebSocket."""
        await self.websocket.send(message)

    async def receive_message(self):
        """Получить ответ из WebSocket."""
        pesto = await self.websocket.recv()
        print(pesto)
        return pesto

    async def close(self):
        """Закрыть WebSocket-соединение."""
        if self.websocket:
            await self.websocket.close()

    async def get_websocket_url(self) -> str:
        """Получить список страниц через HTTP-запрос и выбрать подходящий WebSocket URL."""
        devtools_url = "http://localhost:9222/json"

        async with aiohttp.ClientSession() as session:
            async with session.get(devtools_url) as response:
                if response.status != 200:
                    print("Failed to retrieve pages list.")
                    return None

                pages = await response.json()

                if not pages:
                    print("No pages found.")
                    return None

                # Выбираем первую страницу (или другую, если нужно)
                first_page = pages[0]
                url = first_page.get("webSocketDebuggerUrl", "")
                print(f"Selected WebSocket URL: {url}")
                return url

