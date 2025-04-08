import asyncio
from typing import Optional

import aiohttp
import websockets

from main.handlers.dom_handler import DOMHandler
from main.handlers.network_handler import NetworkHandler
from main.handlers.page_handler import PageHandler
from main.handlers.runtime_handler import RuntimeHandler


class ChromeDriver:
    def __init__(self, host='127.0.0.1', port=9222):
        self.host = host
        self.port = port
        self.ws_url: Optional[str] = None
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self._page_handler = None
        self._runtime_handler = None
        self._dom_handler = None
        self._network_handler = None

    async def get_websocket_debugger_url(self) -> str:
        """Получаем URL для WebSocket соединения"""
        url = f'http://{self.host}:{self.port}/json/version'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data['webSocketDebuggerUrl']

    async def connect(self) -> None:
        """Устанавливаем соединение и инициализируем обработчики"""
        if self.connection and not self.connection.closed:
            return

        self.ws_url = await self.get_websocket_debugger_url()
        self.connection = await websockets.connect(self.ws_url)

        # Инициализируем обработчики
        self._page_handler = PageHandler(self.connection)
        self._runtime_handler = RuntimeHandler(self.connection)
        self._dom_handler = DOMHandler(self.connection)
        self._network_handler = NetworkHandler(self.connection)

        # Включаем необходимые домены
        await self._page_handler.enable()
        await self._dom_handler.enable()
        await self._network_handler.enable()

        print(f"Connected to {self.ws_url}")

    @property
    def page(self) -> PageHandler:
        """Доступ к обработчику страниц"""
        if not self._page_handler:
            raise RuntimeError("PageHandler not initialized. Call connect() first")
        return self._page_handler

    @property
    def runtime(self) -> RuntimeHandler:
        """Доступ к обработчику runtime"""
        if not self._runtime_handler:
            raise RuntimeError("RuntimeHandler not initialized. Call connect() first")
        return self._runtime_handler

    @property
    def dom(self) -> DOMHandler:
        """Доступ к обработчику DOM"""
        if not self._dom_handler:
            raise RuntimeError("DOMHandler not initialized. Call connect() first")
        return self._dom_handler

    @property
    def network(self) -> NetworkHandler:
        """Доступ к обработчику сети"""
        if not self._network_handler:
            raise RuntimeError("NetworkHandler not initialized. Call connect() first")
        return self._network_handler

    async def close(self) -> None:
        """Закрываем соединение"""
        if self.connection and not self.connection.closed:
            await self.connection.close()
            self.connection = None
            print("Connection closed")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def test_website():
    async with ChromeDriver() as driver:
        # Навигация
        await driver.page.navigate("https://example.com")

        # JavaScript
        title = await driver.runtime.evaluate("document.title")
        print(f"Title: {title['result']['value']}")

        # DOM
        header = await driver.dom.query_selector("h1")
        if header:
            html = await driver.dom.get_outer_html(header)
            print(f"Header: {html['outerHTML']}")

        # Сеть
        async def log_request(request):
            print(f"Request: {request['request']['url']}")

        driver.network.add_request_interceptor(log_request)
        await asyncio.sleep(2)

        # Скриншот
        screenshot = await driver.page.capture_screenshot()
        with open("example.png", "wb") as f:
            f.write(screenshot)


if __name__ == "__main__":
    asyncio.run(test_website())