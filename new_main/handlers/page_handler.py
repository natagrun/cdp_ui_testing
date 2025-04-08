import asyncio
import time

import websockets
import json
import aiohttp
import base64

from new_main.handlers.base_handler import BaseHandler


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
        """Ожидание завершения загрузки страницы и всех вложенных фреймов."""
        print("Waiting for page load event...")
        start_time = time.time()
        active_frames = set()  # Для отслеживания загружающихся фреймов

        while True:
            # Проверка таймаута
            if time.time() - start_time > timeout:
                print("Page load timeout reached!")
                break

            try:
                response = await asyncio.wait_for(self.client.receive_message(), timeout=1)
            except asyncio.TimeoutError:
                # Если нет событий в течение timeout, проверяем, все ли фреймы загружены
                if not active_frames:
                    print("All frames loaded!")
                    break
                continue

            response_data = json.loads(response)
            method = response_data.get("method")

            if method == "Page.frameStartedLoading":
                frame_id = response_data["params"]["frameId"]
                active_frames.add(frame_id)
                print(f"Frame {frame_id} started loading")

            elif method == "Page.frameStoppedLoading":
                frame_id = response_data["params"]["frameId"]
                if frame_id in active_frames:
                    active_frames.remove(frame_id)
                    print(f"Frame {frame_id} stopped loading")

            elif method == "Page.frameDetached":
                frame_id = response_data["params"]["frameId"]
                if frame_id in active_frames:
                    active_frames.remove(frame_id)
                    print(f"Frame {frame_id} detached")

            # Также можно добавить обработку других событий, если нужно
            elif method == "Page.loadEventFired":
                print("Main page load event fired")

        print("Page load completed!")

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

