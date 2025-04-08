from typing import Dict, List, Any, Optional

from main.handlers.base_handler import BaseHandler


class RuntimeHandler(BaseHandler):
    def __init__(self, connection):
        super().__init__(connection)
        self._enabled = False

    async def enable(self):
        if not self._enabled:
            await self.send_command("Runtime.enable")
            self._enabled = True

    async def evaluate(self, expression: str, await_promise: bool = False) -> Any:
        """Выполнение JavaScript"""
        return await self.send_command("Runtime.evaluate", {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True
        })

    async def get_properties(self, object_id: str) -> Dict:
        """Получение свойств объекта"""
        return await self.send_command("Runtime.getProperties", {
            "objectId": object_id
        })

    async def call_function(self, function_declaration: str, args: List[Any], object_id: Optional[str] = None) -> Any:
        """Вызов функции"""
        params = {
            "functionDeclaration": function_declaration,
            "arguments": [{"value": arg} for arg in args],
            "returnByValue": True
        }
        if object_id:
            params["objectId"] = object_id

        return await self.send_command("Runtime.callFunctionOn", params)