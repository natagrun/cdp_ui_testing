import asyncio
import base64
import json
import time

from main.handlers.base_handler import BaseHandler
from main.utils.parser import parse_response

class PageHandler(BaseHandler):
    """
    Обработчик команд протокола Page в Chrome DevTools Protocol.
    Предоставляет методы навигации, ожидания загрузки, получения метрик и скриншотов.
    """
    def __init__(self, websocket_client, logger_obj):
        super().__init__(websocket_client,logger_obj)
        self.log = logger_obj.getChild("PageHandler")

    async def enable_page(self):
        """
        Активирует протокол Page.

        :return: Ответ CDP в формате словаря
        """
        self.log.info("Включаем домен Page")
        response = await self.send_request("Page.enable")
        self.log.debug(f"Page.enable ответ: {response}")
        return response

    async def navigate(self, url: str):
        """
        Переходит по указанному URL и ожидает загрузки страницы.

        :param url: Целевой URL
        :return: Ответ CDP от команды navigate
        """
        self.log.info(f"Переходим на страницу {url}")
        response = await self.send_request("Page.navigate", {"url": url})
        self.log.debug(f"Page.navigate ответ: {response}")
        await self.wait_for_page_load()
        return response

    async def wait_for_page_load(self, timeout=30):
        """
        Ожидает полной загрузки страницы по событиям CDP.

        :param timeout: Максимальное время ожидания (в секундах)
        """
        self.log.info("Ждем полную загрузку страницы...")
        start_time = time.time()
        active_frames = set()
        load_event_fired = False

        while True:
            if time.time() - start_time > timeout:
                self.log.warning("Истек таймаут ожидания страниц")
                break

            try:
                response = await asyncio.wait_for(self.client.receive_message(), timeout=1)
                if not response:
                    continue
                response_data = json.loads(response)
            except asyncio.TimeoutError:
                if load_event_fired and not active_frames:
                    self.log.info("Пришло событие 'Load event fired' и "
                                  "нет активных фреймов — делаем вывод что страница загружена")
                    break
                continue
            except Exception as e:
                self.log.exception(f"Ошибка в приеме сообщений загрузки страницы: {e}")
                continue

            method = response_data.get("method")
            params = response_data.get("params", {})
            frame_id = params.get("frameId")

            if method == "Page.frameStartedLoading" and frame_id:
                active_frames.add(frame_id)
            elif method in ["Page.frameStoppedLoading", "Page.frameDetached"] and frame_id:
                active_frames.discard(frame_id)
            elif method == "Page.loadEventFired":
                load_event_fired = True

        self.log.info("Страница загружена")

    async def wait_for_page_dom_load(self, timeout=3, inactivity_timeout=0.2):
        """
        Ожидает стабилизации DOM-дерева страницы по активности и фреймам.

        :param timeout: Общее время ожидания
        :param inactivity_timeout: Период неактивности для завершения ожидания
        :return: Словарь с результатами ожидания
        """
        self.log.info("Ждем стабилизации DOM...")
        start_time = time.time()
        last_activity = time.time()
        active_frames = set()
        dom_activity_detected = False
        load_event_fired = False

        while True:
            now = time.time()
            if now - start_time > timeout:
                self.log.warning("Достигнут таймаут в ожидании DOM")
                break
            if now - last_activity > inactivity_timeout:
                self.log.info("DOM не проявляет активности назначенное время"
                              "делаем вывод что DOM стабилизирован")
                break

            try:
                wait_time = max(0.05, inactivity_timeout - (now - last_activity))
                response = await asyncio.wait_for(self.client.receive_message(), timeout=wait_time)
                if not response:
                    continue
                data = json.loads(response)
                method = data.get("method")
                params = data.get("params", {})
                last_activity = time.time()

                frame_id = params.get("frameId")
                if method == "Page.frameStartedLoading" and frame_id:
                    active_frames.add(frame_id)
                    dom_activity_detected = True
                elif method in ["Page.frameStoppedLoading", "Page.frameDetached"] and frame_id:
                    active_frames.discard(frame_id)
                elif method in ["DOM.childNodeInserted", "DOM.childNodeRemoved", "DOM.attributeModified",
                                "DOM.inlineStyleInvalidated"]:
                    dom_activity_detected = True
                elif method == "Page.loadEventFired":
                    load_event_fired = True
                    if not active_frames:
                        break

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.log.error(f"Ошибка в проверке активности DOM: {e}")

        duration = time.time() - start_time
        self.log.info(f"Загрузка DOM завершена за {duration:.2f}s")
        return {
            "status": "completed",
            "active_frames": len(active_frames),
            "dom_activity": dom_activity_detected,
            "load_event_fired": load_event_fired,
            "duration": duration
        }

    async def reload(self):
        """
        Перезагружает текущую страницу и ожидает загрузку.

        :return: Ответ CDP от Page.reload
        """
        self.log.info("Перезагрузка страницы...")
        response = await self.send_request("Page.reload")
        await self.wait_for_page_load()
        return response

    async def capture_screenshot(self, format="png", quality=20, clip=None):
        """
        Делает скриншот текущей страницы и сохраняет в файл.

        :param format: Формат изображения (по умолчанию png)
        :param quality: Качество (для jpeg)
        :param clip: Область для скриншота
        :return: Ответ CDP от captureScreenshot
        """
        self.log.info("Создание скриншота...")
        params = {"format": format, "quality": quality}
        if clip:
            params["clip"] = clip

        response = await self.send_request("Page.captureScreenshot", params)
        parsed = await parse_response(response)
        screenshot_data = parsed.get("result", {}).get("data")

        if screenshot_data:
            img_data = base64.b64decode(screenshot_data)
            name = str(time.time())+"screenshot.png"
            with open(f"../main/{name}", "wb") as file:
                file.write(img_data)
            self.log.info(f"Скриншот сохранен в ../main/{name}")

        return response

    async def stop_loading(self):
        """
        Прерывает текущую загрузку страницы.

        :return: Ответ CDP от Page.stopLoading
        """
        self.log.info("Прерываем загрузку страницы")
        response = await self.send_request("Page.stopLoading")
        return response

    async def add_script_to_evaluate_on_new_document(self, script: str):
        """
        Добавляет скрипт, который будет выполняться на каждой новой странице.

        :param script: JS-код для выполнения
        :return: Ответ CDP от Page.addScriptToEvaluateOnNewDocument
        """
        self.log.info("Добавляем скрипт, который будет выполняться на каждой новой странице.")
        params = {"source": script}
        response = await self.send_request("Page.addScriptToEvaluateOnNewDocument", params)
        return response

    async def get_layout_metrics(self):
        """
        Получает информацию о текущей раскладке страницы.

        :return: Ответ CDP от Page.getLayoutMetrics
        """
        self.log.info("Получаем информацию о текущей раскладке страницы.")
        response = await self.send_request("Page.getLayoutMetrics")
        return response

    async def setup_page_navigation_listeners(self):
        """
        Включает отслеживание появления новых целей/вкладок.

        :return: None
        """
        self.log.info("Включает отслеживание появления новых целей/вкладок.")
        response = await self.send_request("Target.setDiscoverTargets", {"discover": True})
        self.log.debug(f"Ответ: {response}")
        while True:
            query_response = await self.client.receive_message()
            parsed_query = await parse_response(query_response)
            self.log.debug(f"Целевой ответ: {parsed_query}")

    async def wait_for_navigation(self, timeout=10):
        """
        Ожидает навигации и возвращает новый URL.

        :param timeout: Таймаут в секундах
        :return: URL новой страницы или None
        """
        self.log.info("Ожидаем навигацию")
        try:
            navigation_event = await asyncio.wait_for(self._wait_for_navigation_event(), timeout=timeout)
            return navigation_event
        except asyncio.TimeoutError:
            self.log.warning("Таймаут навигации")
            return None

    async def _wait_for_navigation_event(self):
        """
        Внутренний метод ожидания события перехода по ссылке.

        :return: URL страницы
        """
        while True:
            response = await self.client.receive_message()
            data = await parse_response(response)
            if data.get("method") == "Page.frameNavigated":
                return data["params"]["frame"]["url"]
            elif data.get("method") == "Target.attachedToTarget":
                return data["params"]["targetInfo"]["url"]
