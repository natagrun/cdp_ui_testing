# ===== ElementFinder =====
from typing import Optional

from main.handlers.base_handler import BaseHandler
from main.objects.element import Element
from main.utils.parsers import parse_response  # Вынесем общую функцию


class ElementFinder(BaseHandler):
    async def perform_search(self, xpath: str) -> Optional[str]:
        params = {"query": xpath, "includeUserAgentShadowDOM": True}
        response = await self.send_request("DOM.performSearch", params)
        parsed = parse_response(response)
        return parsed.get("searchId")

    async def get_search_results(self, search_id: str) -> Optional[int]:
        params = {"searchId": search_id, "fromIndex": 0, "toIndex": 1}
        response = await self.send_request("DOM.getSearchResults", params)
        parsed = parse_response(response)
        ids = parsed.get("result", {}).get("nodeIds", [])
        return ids[0] if ids else None

    async def find_element_by_xpath(self, xpath: str) -> Optional[Element]:
        search_id = await self.perform_search(xpath)
        if not search_id:
            return None
        node_id = await self.get_search_results(search_id)
        if not node_id:
            return None
        return Element(
            node_id=node_id,
            backend_node_id=0,
            node_name="",
            box_model=None,
            document_url=None,
            dom_handler=self
        )


# ===== MouseController =====
from main.utils.geometry import get_center_coordinates


class MouseController(BaseHandler):
    async def move_mouse(self, x: float, y: float):
        await self.send_request("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": x,
            "y": y,
            "modifiers": 0,
            "button": "none",
            "buttons": 0
        })

    async def move_mouse_on_element(self, element: Element):
        if not element.box_model:
            return False
        x, y = await get_center_coordinates(element.box_model)
        await self.move_mouse(x, y)

    async def press_mouse(self, x: float, y: float):
        await self.send_request("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "modifiers": 0,
            "button": "left",
            "buttons": 1,
            "clickCount": 1
        })

    async def release_mouse(self, x: float, y: float):
        await self.send_request("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "modifiers": 0,
            "button": "left",
            "buttons": 0,
            "clickCount": 1
        })

    async def highlight_element_border(self, node_id: int, color="red", thickness="2px", duration=10.0) -> bool:
        resolved = await self.send_request("DOM.resolveNode", {
            "nodeId": node_id,
            "objectGroup": "highlight"
        })
        object_id = resolved.get("result", {}).get("object", {}).get("objectId")
        if not object_id:
            return False
        func = f"""
            function () {{
                if (!this || !this.style) return false;
                const original = this.style.border;
                this.style.border = '{thickness} solid {color}';
                setTimeout(() => {{
                    this.style.border = original;
                }}, {int(duration * 1000)});
                return true;
            }}
        """
        response = await self.send_request("Runtime.callFunctionOn", {
            "objectId": object_id,
            "functionDeclaration": func,
            "returnByValue": True
        })
        return response.get("result", {}).get("value") is True


# ===== ScrollController =====
class ScrollController(BaseHandler):
    async def scroll_to_coordinates(self, x: int, y: int) -> bool:
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"window.scrollTo({x}, {y})",
                "awaitPromise": False
            })
            parsed = parse_response(response)
            return not parsed.get("exceptionDetails")
        except Exception:
            return False

    async def scroll_to_element(self, element: Element) -> bool:
        if not element or not element.node_id:
            return False
        try:
            if not element.box_model:
                return False
            x, y = await get_center_coordinates(element.box_model)
            return await self.scroll_to_coordinates(x, y)
        except Exception:
            return False

    async def scroll_by(self, delta_x: int = 0, delta_y: int = 0) -> bool:
        try:
            response = await self.send_request("Input.synthesizeScrollGesture", {
                "x": 100,
                "y": 100,
                "xDistance": delta_x,
                "yDistance": -delta_y,
                "speed": 1000
            })
            parsed = parse_response(response)
            if not parsed.get("error"):
                return True
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"window.scrollBy({delta_x}, {delta_y})",
                "awaitPromise": False
            })
            parsed = parse_response(response)
            return not parsed.get("exceptionDetails")
        except Exception:
            return False

    async def smooth_scroll_to_element(self, element: Element) -> bool:
        if not element or not element.node_id:
            return False
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"""
                    (function() {{
                        const node = document.querySelector('[data-cdp-node-id="{element.node_id}"]');
                        if (node) {{
                            node.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center',
                                inline: 'center'
                            }});
                        }}
                        return !!node;
                    }})()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            parsed = parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value") is True
        except Exception:
            return False


# ===== ElementHelper =====
class ElementHelper(BaseHandler):
    async def get_outer_html(self, node_id: int) -> Optional[str]:
        try:
            response = await self.send_request("DOM.getOuterHTML", {"nodeId": node_id})
            parsed = parse_response(response)
            return parsed.get("result", {}).get("outerHTML")
        except Exception:
            return None

    async def get_inner_html(self, node_id: int) -> Optional[str]:
        try:
            response = await self.send_request("DOM.getInnerHTML", {"nodeId": node_id})
            parsed = parse_response(response)
            return parsed.get("result", {}).get("innerHTML")
        except Exception:
            return None

    async def get_attributes(self, element: Element) -> Optional[Dict[str, str]]:
        try:
            response = await self.send_request("DOM.getAttributes", {"nodeId": element.node_id})
            parsed = parse_response(response)
            attributes = parsed.get("result", {}).get("attributes", [])
            return dict(zip(attributes[::2], attributes[1::2]))
        except Exception:
            return None

    async def get_text(self, element: Element) -> Optional[str]:
        try:
            outer_html = await self.get_outer_html(element.node_id)
            if not outer_html:
                return None
            import json
            html_escaped = json.dumps(outer_html)
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"(function() {{ const div = document.createElement('div'); div.innerHTML = {html_escaped}; return div.textContent || div.innerText || ''; }})()",
                "returnByValue": True
            })
            parsed = parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value")
        except Exception:
            return None


# ===== DOMContext =====
class DOMContext:
    def __init__(self, client):
        self.finder = ElementFinder(client)
        self.mouse = MouseController(client)
        self.scroll = ScrollController(client)
        self.helper = ElementHelper(client)

    async def find_and_click(self, xpath: str):
        element = await self.finder.find_element_by_xpath(xpath)
        if not element:
            return False
        await self.mouse.move_mouse_on_element(element)
        await self.mouse.press_mouse(*await get_center_coordinates(element.box_model))
        await self.mouse.release_mouse(*await get_center_coordinates(element.box_model))
        return True
