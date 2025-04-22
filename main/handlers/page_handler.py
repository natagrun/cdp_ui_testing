import asyncio
import base64
import json
import logging
import time

from main.handlers.base_handler import BaseHandler
from main.utils.parser import parse_response

logger = logging.getLogger(__name__)


class PageHandler(BaseHandler):
    """
    Обработчик команд протокола Page в Chrome DevTools Protocol.
    Предоставляет методы навигации, ожидания загрузки, получения метрик и скриншотов.
    """

    async def enable_page(self):
        """
        Активирует протокол Page.

        :return: Ответ CDP в формате словаря
        """
        logger.info("Enabling Page domain")
        response = await self.send_request("Page.enable")
        logger.debug(f"Page.enable response: {response}")
        return response

    async def navigate(self, url: str):
        """
        Переходит по указанному URL и ожидает загрузки страницы.

        :param url: Целевой URL
        :return: Ответ CDP от команды navigate
        """
        logger.info(f"Navigating to {url}")
        response = await self.send_request("Page.navigate", {"url": url})
        logger.debug(f"Page.navigate response: {response}")
        await self.wait_for_page_load()
        return response

    async def wait_for_page_load(self, timeout=30):
        """
        Ожидает полной загрузки страницы по событиям CDP.

        :param timeout: Максимальное время ожидания (в секундах)
        """
        logger.info("Waiting for full page load...")
        start_time = time.time()
        active_frames = set()
        load_event_fired = False

        while True:
            if time.time() - start_time > timeout:
                logger.warning("Timeout while waiting for page load")
                break

            try:
                response = await asyncio.wait_for(self.client.receive_message(), timeout=1)
                if not response:
                    continue
                response_data = json.loads(response)
            except asyncio.TimeoutError:
                if load_event_fired and not active_frames:
                    logger.info("Load event fired and no active frames — assuming page loaded")
                    break
                continue
            except Exception as e:
                logger.exception(f"Error while receiving page load message: {e}")
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

        logger.info("Page load completed")

    async def wait_for_page_dom_load(self, timeout=3, inactivity_timeout=0.2):
        """
        Ожидает стабилизации DOM-дерева страницы по активности и фреймам.

        :param timeout: Общее время ожидания
        :param inactivity_timeout: Период неактивности для завершения ожидания
        :return: Словарь с результатами ожидания
        """
        logger.info("Waiting for DOM stability...")
        start_time = time.time()
        last_activity = time.time()
        active_frames = set()
        dom_activity_detected = False
        load_event_fired = False

        while True:
            now = time.time()
            if now - start_time > timeout:
                logger.warning("Timeout reached while waiting for DOM")
                break
            if now - last_activity > inactivity_timeout:
                logger.info("DOM inactivity period reached — assuming stable DOM")
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
                logger.error(f"Error while checking DOM activity: {e}")

        duration = time.time() - start_time
        logger.info(f"DOM load completed in {duration:.2f}s")
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
        logger.info("Reloading page...")
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
        logger.info("Capturing screenshot...")
        params = {"format": format, "quality": quality}
        if clip:
            params["clip"] = clip

        response = await self.send_request("Page.captureScreenshot", params)
        parsed = await parse_response(response)
        screenshot_data = parsed.get("result", {}).get("data")

        if screenshot_data:
            img_data = base64.b64decode(screenshot_data)
            with open("../main/screenshot.png", "wb") as file:
                file.write(img_data)
            logger.info("Screenshot saved to ../main/screenshot.png")

        return response

    async def stop_loading(self):
        """
        Прерывает текущую загрузку страницы.

        :return: Ответ CDP от Page.stopLoading
        """
        logger.info("Stopping page load")
        response = await self.send_request("Page.stopLoading")
        return response

    async def add_script_to_evaluate_on_new_document(self, script: str):
        """
        Добавляет скрипт, который будет выполняться на каждой новой странице.

        :param script: JS-код для выполнения
        :return: Ответ CDP от Page.addScriptToEvaluateOnNewDocument
        """
        logger.info("Adding script to evaluate on new document")
        params = {"source": script}
        response = await self.send_request("Page.addScriptToEvaluateOnNewDocument", params)
        return response

    async def get_layout_metrics(self):
        """
        Получает информацию о текущей раскладке страницы.

        :return: Ответ CDP от Page.getLayoutMetrics
        """
        logger.info("Getting layout metrics")
        response = await self.send_request("Page.getLayoutMetrics")
        return response

    async def setup_page_navigation_listeners(self):
        """
        Включает отслеживание появления новых целей/вкладок.

        :return: None
        """
        logger.info("Setting up navigation listeners")
        response = await self.send_request("Target.setDiscoverTargets", {"discover": True})
        logger.debug(f"Target discovery response: {response}")
        while True:
            query_response = await self.client.receive_message()
            parsed_query = await parse_response(query_response)
            logger.debug(f"Target event received: {parsed_query}")

    async def wait_for_navigation(self, timeout=10):
        """
        Ожидает навигации и возвращает новый URL.

        :param timeout: Таймаут в секундах
        :return: URL новой страницы или None
        """
        logger.info("Waiting for navigation event")
        try:
            navigation_event = await asyncio.wait_for(self._wait_for_navigation_event(), timeout=timeout)
            return navigation_event
        except asyncio.TimeoutError:
            logger.warning("Navigation timeout")
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
