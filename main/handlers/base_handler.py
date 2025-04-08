import asyncio
import json
import logging
import time
from collections import defaultdict

import json
import asyncio
from typing import Dict, Any, Optional, List
from collections import defaultdict

import json
import asyncio
from collections import defaultdict
from typing import Dict, Any, Optional, List, Callable, Awaitable

import json
import asyncio
from typing import Optional, Dict, Any
from collections import defaultdict

import websockets


class BaseHandler:
    def __init__(self, connection):
        self.connection = connection
        self._pending_requests = {}
        self._event_listeners = defaultdict(list)
        self._next_id = 1
        self._message_handler_task = None

    async def start(self):
        """Запускает обработчик входящих сообщений"""
        self._message_handler_task = asyncio.create_task(self._handle_messages())

    async def stop(self):
        """Останавливает обработчик сообщений"""
        if self._message_handler_task:
            self._message_handler_task.cancel()
            try:
                await self._message_handler_task
            except asyncio.CancelledError:
                pass

    async def _handle_messages(self):
        """Непрерывно обрабатывает входящие сообщения"""
        while True:
            try:
                message = await self.connection.recv()
                message = json.loads(message)
                await self._process_message(message)
            except (websockets.exceptions.ConnectionClosed, json.JSONDecodeError) as e:
                print(f"Connection error: {e}")
                break

    async def _process_message(self, message: Dict):
        """Обрабатывает одно входящее сообщение"""
        if 'id' in message and message['id'] in self._pending_requests:
            future = self._pending_requests.pop(message['id'])
            if 'error' in message:
                future.set_exception(Exception(message['error']['message']))
            else:
                future.set_result(message.get('result'))
        elif 'method' in message:
            for callback in self._event_listeners.get(message['method'], []):
                asyncio.create_task(callback(message.get('params')))

    async def send_command(self, method: str, params: Optional[Dict] = None, timeout: int = 30) -> Any:
        """Улучшенная отправка команд с обработкой ошибок"""
        if params is None:
            params = {}

        if not self.connection or self.connection.closed:
            raise ConnectionError("WebSocket connection is closed")

        request_id = self._next_id
        self._next_id += 1

        message = {
            'id': request_id,
            'method': method,
            'params': params
        }

        future = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            await self.connection.send(json.dumps(message))
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            del self._pending_requests[request_id]
            raise TimeoutError(f"Command {method} timed out after {timeout} seconds")
        except Exception as e:
            del self._pending_requests[request_id]
            raise ConnectionError(f"Failed to send command: {str(e)}")

