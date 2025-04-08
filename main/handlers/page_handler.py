import asyncio
import base64
import logging
from io import BytesIO

from PIL import Image

from main.handlers.base_handler import BaseHandler


class PageHandler(BaseHandler):

    def __init__(self, connection):
        super().__init__(connection)
        self._enabled = False

    async def enable(self):
        if not self._enabled:
            await self.send_command("Page.enable")
            self._enabled = True

    async def disable(self):
        """Отключение событий страницы"""
        await self.send_command("Page.disable")

    async def navigate(self, url: str, wait_until: str = "load"):
        """Навигация на URL"""
        await self.send_command("Page.navigate", {
            "url": url,
            "waitUntil": wait_until
        })

    async def reload(self, ignore_cache: bool = False):
        """Перезагрузка страницы"""
        await self.send_command("Page.reload", {
            "ignoreCache": ignore_cache
        })

    async def capture_screenshot(self, format: str = "png", full_page: bool = False) -> bytes:
        """Скриншот страницы"""
        params = {
            "format": format,
            "clip": {
                "x": 0,
                "y": 0,
                "width": 1920,
                "height": 1080,
                "scale": 1
            }
        }
        if full_page:
            metrics = await self.send_command("Page.getLayoutMetrics")
            params["clip"] = {
                "x": 0,
                "y": 0,
                "width": metrics["contentSize"]["width"],
                "height": metrics["contentSize"]["height"],
                "scale": 1
            }

        result = await self.send_command("Page.captureScreenshot", params)
        return result["data"]

    async def emulate_device(self, device_name: str):
        """Эмуляция устройства"""
        devices = {
            "iPhone 12": {
                "width": 390,
                "height": 844,
                "deviceScaleFactor": 3,
                "mobile": True
            },
            "iPad": {
                "width": 768,
                "height": 1024,
                "deviceScaleFactor": 2,
                "mobile": True
            }
        }

        if device_name not in devices:
            raise ValueError(f"Unknown device: {device_name}")

        await self.send_command("Emulation.setDeviceMetricsOverride", devices[device_name])
