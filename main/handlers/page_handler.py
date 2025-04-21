import asyncio
import base64
import json
import logging
import time
from typing import Dict, Union

from main.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)

async def _parse_response(response: Union[str, Dict]) -> Dict:
    """Парсит ответ CDP (может быть строкой JSON или уже словарём)."""
    if isinstance(response, str):
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CDP response: {e}")
            return {}
    return response


class PageHandler(BaseHandler):
    """Обработчик команд для страницы."""

    async def enable_page(self):
        """Активировать протокол Page."""
        response = await self.send_request("Page.enable")
        print(f"Response from Page.enable: {response}")
        return response

    async def navigate(self, url: str):
        """Перейти по указанному URL и дождаться полной загрузки страницы."""
        params = {"url": url}
        response = await self.send_request("Page.navigate", params)
        print(f"Page navigation response: {response}")

        # Ожидаем завершения загрузки страницы
        await self.wait_for_page_load()

        return response

    async def wait_for_page_load(self, timeout=30):
        """
        Ожидает полной загрузки страницы и фреймов, основываясь на событиях CDP.
        Более устойчивая версия с логированием и защитой от сбоев.
        """
        logger.info("Waiting for page load...")
        start_time = time.time()
        active_frames = set()
        load_event_fired = False

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.warning("Page load timeout reached!")
                break

            try:
                response = await asyncio.wait_for(self.client.receive_message(), timeout=1)
                if response is None:
                    logger.warning("Received empty response")
                    continue

                response_data = json.loads(response)
            except asyncio.TimeoutError:
                if load_event_fired and not active_frames:
                    logger.info("No active frames and load event fired — assuming page loaded.")
                    break
                continue
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode response: {e}")
                continue
            except Exception as e:
                logger.exception(f"Unexpected error while receiving message: {e}")
                break

            method = response_data.get("method")
            params = response_data.get("params", {})

            if method == "Page.frameStartedLoading":
                frame_id = params.get("frameId")
                if frame_id:
                    active_frames.add(frame_id)
                    logger.debug(f"Frame {frame_id} started loading")

            elif method == "Page.frameStoppedLoading":
                frame_id = params.get("frameId")
                if frame_id:
                    active_frames.discard(frame_id)
                    logger.debug(f"Frame {frame_id} stopped loading")

            elif method == "Page.frameDetached":
                frame_id = params.get("frameId")
                if frame_id:
                    active_frames.discard(frame_id)
                    logger.debug(f"Frame {frame_id} detached")

            elif method == "Page.loadEventFired":
                load_event_fired = True
                logger.debug("Main page load event fired")

            if load_event_fired and not active_frames:
                logger.info("All frames loaded and load event fired.")
                break

        logger.info("Page load completed.")

    async def wait_for_page_dom_load(self, timeout=3, inactivity_timeout=0.2):
        """
        Ожидание завершения загрузки страницы с отслеживанием DOM-активности и фреймов.

        Args:
            timeout: Максимальное время ожидания (сек)
            inactivity_timeout: Время без событий для досрочного завершения (сек)
        """
        logger.info(f"Waiting for DOM stability (timeout={timeout}s, inactivity={inactivity_timeout}s)...")
        start_time = time.time()
        last_activity = time.time()
        active_frames = set()
        dom_activity_detected = False
        load_event_fired = False

        while True:
            now = time.time()

            # Общий таймаут
            if now - start_time > timeout:
                logger.warning("DOM wait timeout reached.")
                break

            # Неактивность — если давно не было событий
            if now - last_activity > inactivity_timeout:
                logger.info("No activity detected. Assuming page is stable.")
                break

            try:
                wait_time = max(0.05, inactivity_timeout - (now - last_activity))
                response = await asyncio.wait_for(self.client.receive_message(), timeout=wait_time)
                if not response:
                    continue

                data = json.loads(response)
                method = data.get("method")
                params = data.get("params", {})
                last_activity = time.time()  # Обновляем метку активности

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                continue

            # === События загрузки фреймов ===
            frame_id = params.get("frameId")
            if method == "Page.frameStartedLoading" and frame_id:
                active_frames.add(frame_id)
                logger.debug(f"Frame {frame_id} started loading")
                dom_activity_detected = True

            elif method == "Page.frameStoppedLoading" and frame_id:
                active_frames.discard(frame_id)
                logger.debug(f"Frame {frame_id} stopped loading")

            elif method == "Page.frameDetached" and frame_id:
                active_frames.discard(frame_id)
                logger.debug(f"Frame {frame_id} detached")

            # === DOM-активность ===
            elif method in ["DOM.childNodeInserted", "DOM.childNodeRemoved",
                            "DOM.attributeModified", "DOM.inlineStyleInvalidated"]:
                logger.debug(f"DOM activity detected: {method}")
                dom_activity_detected = True

            # === Загрузка страницы ===
            elif method == "Page.loadEventFired":
                logger.debug("Page load event fired")
                load_event_fired = True
                if not active_frames:
                    logger.debug("All frames loaded after load event — early exit")
                    break

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
        """Перезагрузить страницу."""
        response = await self.send_request("Page.reload")
        print(f"Page reload response: {response}")
        await self.wait_for_page_load()
        return response

    async def capture_screenshot(self, format="png", quality=20, clip=None):
        """Сделать скриншот страницы."""
        # await sleep(5)
        params = {"format": format, "quality": quality}
        if clip:
            params["clip"] = clip

        response = await self.send_request("Page.captureScreenshot", params)
        print(f"Page screenshot captured: {response}")

        # Если ответ содержит изображение, преобразуем его в base64
        screenshot_data = json.loads(response).get("result", {}).get("data")
        if screenshot_data:
            # Декодируем изображение в base64
            img_data = base64.b64decode(screenshot_data)
            with open("../main/screenshot.png", "wb") as file:
                file.write(img_data)
            print("Screenshot saved as screenshot.png")
        # await sleep(5)
        return response

    async def stop_loading(self):
        """Остановить загрузку страницы."""
        response = await self.send_request("Page.stopLoading")
        print(f"Page stop loading response: {response}")
        return response

    async def add_script_to_evaluate_on_new_document(self, script: str):
        """Добавить скрипт для выполнения на каждой новой загружаемой странице."""
        params = {"source": script}
        response = await self.send_request("Page.addScriptToEvaluateOnNewDocument", params)
        print(f"Script added to evaluate on new document: {response}")
        return response

    async def get_layout_metrics(self):
        response = await self.send_request("Page.getLayoutMetrics")
        print(f"Layout metrics: {response}")
        return response

    async def setup_page_navigation_listeners(self):
        """Включает отслеживание навигации и новых вкладок."""
        # Включаем необходимые домены
        # await self.send_request("Page.enable")
        response = await self.send_request("Target.setDiscoverTargets", {"discover": True})
        parsed_query = await _parse_response(response)
        logger.error(parsed_query)
        while True:
            query_response = await self.client.receive_message()
            parsed_query = await _parse_response(query_response)
            logger.error(parsed_query)
            # if parsed_query.get("id") is not None:
            #     break


    async def wait_for_navigation(self, timeout=10):
        """
        Ожидает навигации на новой странице.
        Возвращает URL новой страницы или None, если навигации не было.
        """
        try:
            # Получаем текущий URL
            original_url = await self.get_current_url()

            # Ожидаем событие навигации
            navigation_event = await asyncio.wait_for(
                self._wait_for_navigation_event(),
                timeout=timeout
            )
            return navigation_event
        except asyncio.TimeoutError:
            return None

    async def _wait_for_navigation_event(self):
        """
        Внутренний метод для ожидания событий навигации.
        """
        while True:
            response = await self.client.receive_message()
            data = json.loads(response)

            # Проверяем события навигации
            if data.get("method") == "Page.frameNavigated":
                return data["params"]["frame"]["url"]
            elif data.get("method") == "Target.attachedToTarget":
                return data["params"]["targetInfo"]["url"]

    async def get_current_url(self):
        """Возвращает текущий URL страницы."""
        response = await self.send_request("Page.getNavigationHistory")
        data = json.loads(response)
        return data["result"]["entries"][-1]["url"]
