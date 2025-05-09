# main/handlers/runtime_handler.py
from typing import Any, Optional

from main.handlers.base_handler import BaseHandler
from main.utils.parser import parse_response


class RuntimeHandler(BaseHandler):
    """Все методы CDP. Runtime.* + вспомогательные JS-утилиты"""
    def __init__(self, websocket_client,logger_obj):
        super().__init__(websocket_client,logger_obj)
        self.log = logger_obj.getChild("RuntimeHandler")

    async def evaluate(self, expression: str,
                       return_by_value: bool = True,
                       await_promise: bool = False) -> Any:
        resp = await self.send_request("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": await_promise
        })
        return await parse_response(resp)

    async def call_function_on(self, object_id: str,
                               function_declaration: str,
                               return_by_value: bool = True) -> Any:
        resp = await self.send_request("Runtime.callFunctionOn", {
            "objectId": object_id,
            "functionDeclaration": function_declaration,
            "returnByValue": return_by_value
        })
        return await parse_response(resp)

    async def resolve_node(self, node_id: int,
                           object_group: Optional[str] = None) -> Any:
        params = {"nodeId": node_id}
        if object_group:
            params["objectGroup"] = object_group
        resp = await self.send_request("DOM.resolveNode", params)
        return await parse_response(resp)

    async def clear_value(self, node_id: int) -> bool:
        """Очистить value или contentEditable через JS."""
        # получаем objectId
        resolved = await self.resolve_node(node_id)
        oid = resolved["result"]["object"]["objectId"]
        if not oid:
            return False

        js = """
            function() {
                if ('value' in this) {
                    this.value = '';
                } else if (this.isContentEditable) {
                    this.innerText = '';
                }
                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
        """
        resp = await self.call_function_on(oid, js)
        return resp.get("result", {}).get("value", False) is True