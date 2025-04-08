import base64
import json
import time
import aiohttp
from typing import Any, Dict, Optional, Callable
import websockets



class CDPClient:
    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.websocket = None

    async def connect(self):
        """Подключиться к WebSocket"""
        self.websocket = await websockets.connect(self.websocket_url)

    async def send_command(self, method: str, params: dict = None) -> dict:
        """Отправить команду через WebSocket"""
        if not params:
            params = {}
        message = {
            "id": 1,  # ID запроса (можно сделать уникальным для каждого запроса)
            "method": method,
            "params": params
        }
        await self.websocket.send(json.dumps(message))

        response = await self.websocket.recv()
        return json.loads(response)

    async def close(self):
        """Закрыть соединение"""
        if self.websocket:
            await self.websocket.close()

class PageHandler:
    """Обработчик домена Page"""

    def __init__(self, client: CDPClient):
        self.client = client

    async def enable(self):
        """Активировать обработку событий Page"""
        response = await self.client.send_command("Page.enable")
        print(f"Response from Page.enable: {response}")
        return response

    async def navigate(self, url: str):
        """Перейти по указанному URL"""
        response = await self.client.send_command("Page.navigate", {"url": url})
        print(f"Response from Page.navigate: {response}")
        return response

    async def capture_screenshot(self, format: str = "png") -> str:
        """Сделать скриншот страницы"""
        response = await self.client.send_command("Page.captureScreenshot", {"format": format})
        print(f"Response from Page.captureScreenshot: {response}")
        return response.get('data', '')


class CDPTestFramework:
    """Фреймворк для тестирования UI через Chrome DevTools Protocol"""

    def __init__(self, host: str = "localhost", port: int = 9222):
        self.client = CDPClient(host, port)
        self.page = PageHandler(self.client)

    async def connect(self):
        """Установить соединение с DevTools"""
        await self.client.connect()

        # Активируем основные домены
        await self.page.enable()

    async def close(self):
        """Закрыть соединение"""
        await self.client.close()

    async def wait_for_event(self, event_name: str, timeout: float = 10.0) -> dict:
        """Ожидать наступление события"""
        future = asyncio.Future()

        def callback(params):
            if not future.done():
                future.set_result(params)

        self.client.add_event_listener(event_name, callback)

        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Timeout waiting for event: {event_name}")
        finally:
            if event_name in self.client.event_listeners:
                self.client.event_listeners[event_name].remove(callback)

import asyncio

async def example_usage():
    framework = CDPTestFramework()  # Используем стандартные host и port

    try:
        print("Starting framework...")
        await framework.connect()
        print("Framework connected!")

        # Открыть страницу
        print("Navigating to https://example.com...")
        await framework.page.navigate("https://example.com")

        # Ожидание загрузки страницы с тайм-аутом
        print("Waiting for Page.loadEventFired event...")
        try:
            await asyncio.wait_for(framework.wait_for_event("Page.loadEventFired"), timeout=30.0)
            print("Page loaded!")
        except asyncio.TimeoutError:
            print("Timeout waiting for event: Page.loadEventFired")

        # Сделать скриншот
        print("Capturing screenshot...")
        screenshot = await framework.page.capture_screenshot()
        screenshot_data = base64.b64decode(screenshot)  # Декодируем base64 в бинарные данные
        with open("screenshot.png", "wb") as f:
            f.write(screenshot_data)

        print("Screenshot saved successfully.")

    finally:
        await framework.close()
        print("Framework closed.")
#
# import websockets
# import asyncio
#
# async def test_websocket_connection():
#     url = "ws://localhost:9222/devtools/page/1869D8D81DD4D9B3405A2674EE13E9EB"
#     try:
#         async with websockets.connect(url) as websocket:
#             print("WebSocket connection established!")
#
#             # Активируем протокол Page
#             enable_page = '{"id": 1, "method": "Page.enable"}'
#             await websocket.send(enable_page)
#             response = await websocket.recv()
#             print(f"Response from Page.enable: {response}")
#
#             # Теперь можно выполнять другие команды
#             await websocket.send('{"id":2,"method":"Page.navigate","params":{"url":"https://www.example.com"}}')
#             response = await websocket.recv()
#             print(f"Page navigation response: {response}")
#
#     except Exception as e:
#         print(f"Error: {e}")
#
#


if __name__ == "__main__":
    # asyncio.run(test_websocket_connection())
    asyncio.run(example_usage())

