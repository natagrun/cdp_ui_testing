import platform
from typing import *

from main.handlers.base_handler import BaseHandler
from main.handlers.runtime_handler import RuntimeHandler
from main.utils.math import get_center_coordinates
from main.utils.parser import parse_response


class InputHandler(BaseHandler):
    """Все методы CDP. Input.*"""
    # Битовые маски для модификаторов в CDP
    MODIFIER_MASKS = {
        'alt': 1,
        'ctrl': 2,
        'control': 2,
        'meta': 4,
        'command': 4,
        'cmd': 4,
        'shift': 8,
    }

    def __init__(self, client, logger_obj, runtime_handler: RuntimeHandler = None):
        super().__init__(client,logger_obj)
        self._runtime_handler = runtime_handler or RuntimeHandler(client, logger_obj)
        self.log=logger_obj.getChild("InputHandler")

    async def move_mouse(self, x: float, y: float) -> None:
        await self.send_request("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": x, "y": y,
            "modifiers": 0, "button": "none", "buttons": 0
        })

    async def press_mouse(self, x: float, y: float, button: int = 0) -> None:
        direction = "left" if button == 0 else "right"
        await self.send_request(
            "Input.dispatchMouseEvent",
            {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "modifiers": 0,
                "button": direction,
                "buttons": 1,
                "clickCount": 1,
            }
        )

    async def release_mouse(self, x: float, y: float, button: int = 0) -> None:
        direction = "left" if button == 0 else "right"
        await self.send_request(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "modifiers": 0,
                "button": direction,
                "buttons": 0,
                "clickCount": 1,
            }
        )

    async def move_mouse_on_element(self, element) -> None:
        x, y = await get_center_coordinates(element.box_model)
        await self.move_mouse(x, y)

    async def scroll_to_coordinates(self, x: int, y: int) -> bool:
        """
        Прокручивает страницу к указанным координатам.

        Args:
            x: Горизонтальная координата
            y: Вертикальная координата

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        try:
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"window.scrollTo({x}, {y})",
                "awaitPromise": False
            })
            parsed = await parse_response(response)
            if parsed.get("exceptionDetails"):
                self.log.error(f"Прокрутка вывела ошибку: {parsed.get('exceptionDetails')}")
                return False
            return True
        except Exception as e:
            self.log.error(f"Ошибка прокрутки на координаты: {e}")
            return False

    async def scroll_to_element(self, element) -> bool:
        """
        Прокручивает страницу к указанному элементу.

        Args:
            element: Данные элемента (должен содержать nodeId)

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        if not element or not element.node_id:
            self.log.error("Не передан элемент или элемент пуст")
            return False

        try:
            model = element.box_model
            if not model:
                self.log.error("Нет данных о теле элемента")
                return False

            x, y = await get_center_coordinates(model)
            await self.scroll_to_coordinates(x, y)

        except Exception as ex:
            self.log.error(f"JavaScript прокрутка выдала ошибку: {ex}")
            return False

    async def scroll_by(self, delta_x: int = 0, delta_y: int = 0) -> bool:
        """
        Прокручивает страницу на указанное количество пикселей.

        Args:
            delta_x: Горизонтальное смещение
            delta_y: Вертикальное смещение

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        try:
            # Вариант 1: Через Input.synthesizeScrollGesture (наиболее реалистично)
            response = await self.send_request("Input.synthesizeScrollGesture", {
                "x": 100,  # Стартовая позиция (не важна для простой прокрутки)
                "y": 100,
                "xDistance": delta_x,
                "yDistance": -delta_y,  # Отрицательное значение потому что в CDP направление обратное
                "speed": 1000
            })
            parsed = await parse_response(response)
            if not parsed.get("error"):
                return True

            # Вариант 2: Через JavaScript (fallback)
            response = await self.send_request("Runtime.evaluate", {
                "expression": f"window.scrollBy({delta_x}, {delta_y})",
                "awaitPromise": False
            })
            parsed = await parse_response(response)
            return not parsed.get("exceptionDetails")
        except Exception as e:
            self.log.error(f"Ошибка прокрутки на дельту: {e}")
            return False

    async def smooth_scroll_to_element(self, element) -> bool:
        """
        Плавно прокручивает страницу к указанному элементу.

        Args:
            element: Данные элемента (должен содержать nodeId)

        Returns:
            bool: True если прокрутка выполнена успешно
        """
        if not element or not element.node_id:
            self.log.error("Не передан жлемент или он пуст")
            return False

        try:
            # Пробуем через JavaScript для плавной прокрутки
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
            parsed = await parse_response(response)
            return parsed.get("result", {}).get("result", {}).get("value") is True
        except Exception as e:
            self.log.error(f"Ошибка прокрутки к элементу: {e}")
            return False

    async def clear_field(self, element) -> bool:
        """
        Очищает содержимое элемента
        """
        try:
            await self._runtime_handler.clear_value(element.node_id)
            return True
        except Exception as e:
            self.log.error(f"Ошибка очстики поля: {e}")
            return False

    async def click_element(self, element) -> bool:
        """
        Кликнуть на элемент с опциональным ожиданием навигации.

        Args:
            element_data: Данные элемента
            wait_for_navigation: Нужно ли ждать навигации после клика
            timeout: Таймаут ожидания навигации (сек)

        Returns:
            Tuple[bool, Optional[str]]: (Успех клика, URL новой страницы или None)
            :param element:
        """
        try:
            if not element:
                self.log.error("Не передан элемент или он пуст")
                return False

            model = element.box_model
            if not model:
                self.log.error("Нет тела элемента")
                return False
            node_id = element.node_id
            if not node_id:
                self.log.error("Нет nodeId жлемента")
                return False
            x, y = await get_center_coordinates(model)

            await self.move_mouse(x, y)
            await self.press_mouse(x, y)
            await self.release_mouse(x, y)
            return True

        except Exception as e:
            self.log.error(f"Ошибка клика: {e}")
            return False

    async def focus_on_element(self, element):
        try:
            response = await self.send_request("DOM.focus", {"nodeId": element.node_id})
            parsed = await parse_response(response)
            print(parsed)
            return parsed.get("result", {}).get("innerHTML")
        except Exception as e:
            self.log.error(f"Ошибка получения innerHTML: {e}")
            return None

    async def insert_text(self, element, text: str) -> bool:
        """
        Вставляет текст в указанный элемент с fallback-механизмом.

        Сначала пробует быстрый JavaScript-метод, если не сработает - использует эмуляцию ввода.

        Args:
            element: Данные элемента (должен содержать nodeId)
            text: Текст для вставки

        Returns:
            bool: True если текст успешно вставлен, False в случае ошибки
            :param text:
            :param element:
        """
        if not element or not element.node_id:
            self.log.error("Не передан элемент или он пуст")
            return False

        node_id = element.node_id

        await self.focus_on_element(element)

        # 1. Сначала пробуем быстрый JavaScript-метод
        js_success = await self._insert_text_via_javascript(node_id, text)
        if js_success:
            self.log.debug(f"Успешно вставлен текст в помощью JavaScript метода")
            return True

        # 2. Если JavaScript-метод не сработал, пробуем медленный метод эмуляции ввода
        self.log.debug("JavaScript провалился, пробуем вставить текст эмуляцией...")
        await self._insert_text_via_input(node_id, text)

        return True

    async def _insert_text_via_javascript(self, node_id: int, text: str) -> bool:
        """Вставляет текст в элемент напрямую через JS, используя RuntimeHandler."""
        try:
            # Получаем objectId через RuntimeHandler.resolve_node
            resolved = await self._runtime_handler.resolve_node(node_id)
            object_id = resolved.get("result", {}).get("object", {}).get("objectId")
            if not object_id:
                self.log.error("Не можем получить objectId из nodeId")
                return False

            # JS-функция для вставки текста
            js_func = f"""
                function() {{
                    if (!this) return false;
                    if ('value' in this) {{
                        this.value = `{text}`;
                    }} else if (this.isContentEditable) {{
                        this.innerText = `{text}`;
                    }} else {{
                        return false;
                    }}
                    this.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    this.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
            """

            # Вызываем через RuntimeHandler.call_function_on
            response = await self._runtime_handler.call_function_on(object_id, js_func)
            success = response.get("result", {}).get("value")
            return success is True

        except Exception as e:
            self.log.error(f"JavaScript ввод текста получил ошибку: {e}")
            return False

    async def _insert_text_via_input(self, node_id: int, text: str) -> bool:
        """Вставляет текст через эмуляцию ввода с клавиатуры"""
        try:
            # Фокусируемся на элементе
            await self.send_request("DOM.focus", {"nodeId": node_id})

            # Очищаем содержимое (Ctrl+A + Backspace)
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "key": "a",
                "modifiers": 2  # Ctrl
            })
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "key": "a",
                "modifiers": 2
            })
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "key": "Backspace",
                "modifiers": 0
            })
            await self.send_request("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "key": "Backspace",
                "modifiers": 0
            })

            # Вводим текст посимвольно
            for char in text:
                await self.send_request("Input.dispatchKeyEvent", {
                    "type": "keyDown",
                    "text": char,
                    "unmodifiedText": char,
                    "key": char,
                    "modifiers": 0
                })
                await self.send_request("Input.dispatchKeyEvent", {
                    "type": "keyUp",
                    "key": char,
                    "modifiers": 0
                })

            return True
        except Exception as e:
            self.log.error(f"Эмуляция ввода получила ошибку: {e}")
            return False

    def _get_modifier_mask(self, modifiers: Optional[List[str]] = None) -> int:
        """
        Вычислить битовую маску модификаторов по списку имён для текущей ОС.
        'Ctrl' на macOS заменяется на 'meta'.
        """
        if not modifiers:
            return 0
        mask = 0
        system = platform.system()
        for mod in modifiers:
            key = mod.lower()
            if key in ('ctrl', 'control'):
                # на macOS Ctrl заменяем на Meta (Cmd)
                if system == 'Darwin':
                    mask |= self.MODIFIER_MASKS['meta']
                else:
                    mask |= self.MODIFIER_MASKS['ctrl']
            elif key in ('meta', 'cmd', 'command'):
                mask |= self.MODIFIER_MASKS['meta']
            elif key in ('alt', 'option'):
                mask |= self.MODIFIER_MASKS['alt']
            elif key == 'shift':
                mask |= self.MODIFIER_MASKS['shift']
        return mask

    async def dispatch_key_event(
            self,
            event_type: str,
            key: str,
            code: str,
            modifiers: Optional[List[str]] = None
    ) -> None:
        """
        Универсальный Input.dispatchKeyEvent для клавиш с учётом модификаторов.

        :param event_type: 'keyDown' или 'keyUp'
        :param key: физическое имя клавиши (например, 'a', 'Backspace')
        :param code: код клавиши по спецификации (например, 'KeyA', 'Backspace')
        :param modifiers: список модификаторов ['ctrl', 'shift'] и т.п.
        """
        await self.send_request(
            'Input.dispatchKeyEvent',
            {
                'type': event_type,
                'key': key,
                'code': code,
                'modifiers': self._get_modifier_mask(modifiers)
            }
        )

    async def press_key(
            self,
            key: str,
            code: str,
            modifiers: Optional[List[str]] = None
    ) -> None:
        """
        Нажать и отпустить клавишу с заданными модификаторами.

        Пример: press_key('a', 'KeyA', ['ctrl', 'shift'])
        """
        await self.dispatch_key_event('keyDown', key, code, modifiers)
        await self.dispatch_key_event('keyUp', key, code, modifiers)
