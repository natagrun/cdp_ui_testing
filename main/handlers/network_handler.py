from typing import Optional, Dict, Any, List, Callable, Awaitable
from urllib.parse import urlparse
import json

from main.handlers.base_handler import BaseHandler


class NetworkHandler(BaseHandler):
    def __init__(self, connection):
        super().__init__(connection)
        self._request_interceptors = []
        self._response_interceptors = []
        self._request_ids = {}
        self._enabled = False

    async def enable(self):
        if not self._enabled:
            await self.send_command("Network.enable")
            self.add_event_listener("Network.requestWillBeSent", self._on_request_will_be_sent)
            self.add_event_listener("Network.responseReceived", self._on_response_received)
            self._enabled = True


    async def _on_request_will_be_sent(self, event: Dict):
        """Обработчик запросов"""
        request_id = event["requestId"]
        self._request_ids[request_id] = event

        for interceptor in self._request_interceptors:
            await interceptor(event)

    async def _on_response_received(self, event: Dict):
        """Обработчик ответов"""
        request_id = event["requestId"]
        request_event = self._request_ids.get(request_id, {})

        combined = {
            "request": request_event.get("request", {}),
            "response": event.get("response", {}),
            "timestamp": event.get("timestamp", 0),
            "requestId": request_id
        }

        for interceptor in self._response_interceptors:
            await interceptor(combined)

    def add_request_interceptor(self, callback: Callable[[Dict], Awaitable[None]]):
        """Добавление перехватчика запросов"""
        self._request_interceptors.append(callback)

    def add_response_interceptor(self, callback: Callable[[Dict], Awaitable[None]]):
        """Добавление перехватчика ответов"""
        self._response_interceptors.append(callback)

