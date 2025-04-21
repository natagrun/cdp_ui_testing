import asyncio
import json
import time
from typing import Optional, Dict, Any

from main.handlers.base_handler import BaseHandler


class EmulationHandler(BaseHandler):
    """Обработчик команд для эмуляции устройств и окружения."""

    async def enable_emulation(self):
        """Активировать протокол Emulation."""
        response = await self.send_request("Emulation.enable")
        print(f"Response from Emulation.enable: {response}")
        return response

    async def set_viewport_size(
            self,
            width: int,
            height: int,
            device_scale_factor: float = 1.0,
            mobile: bool = False,
            screen_width: Optional[int] = None,
            screen_height: Optional[int] = None
    ) -> Dict:
        """
        Установить размер вьюпорта и параметры устройства (аналог setViewportSize).

        Args:
            width: Ширина вьюпорта в пикселях
            height: Высота вьюпорта в пикселях
            device_scale_factor: Масштаб устройства (например, 2 для Retina)
            mobile: Эмулировать мобильное устройство
            screen_width: Ширина экрана (если отличается от вьюпорта)
            screen_height: Высота экрана (если отличается от вьюпорта)
        """
        params = {
            "width": width,
            "height": height,
            "deviceScaleFactor": device_scale_factor,
            "mobile": mobile,
            "screenWidth": screen_width or width,
            "screenHeight": screen_height or height,
        }
        response = await self.send_request("Emulation.setDeviceMetricsOverride", params)
        print(f"Viewport size set to {width}x{height}: {response}")
        return response

    async def set_geolocation(
            self,
            latitude: float,
            longitude: float,
            accuracy: float = 100.0
    ) -> Dict:
        """
        Установить эмулируемую геолокацию.

        Args:
            latitude: Широта
            longitude: Долгота
            accuracy: Точность в метрах
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy
        }
        response = await self.send_request("Emulation.setGeolocationOverride", params)
        print(f"Geolocation set to {latitude},{longitude}: {response}")
        return response

    async def set_user_agent(
            self,
            user_agent: str,
            accept_language: str = "en-US,en;q=0.9",
            platform: str = ""
    ) -> Dict:
        """
        Переопределить User-Agent браузера.

        Args:
            user_agent: Строка User-Agent
            accept_language: Язык для заголовка Accept-Language
            platform: Платформа (например, "iPhone")
        """
        params = {
            "userAgent": user_agent,
            "acceptLanguage": accept_language,
            "platform": platform
        }
        response = await self.send_request("Emulation.setUserAgentOverride", params)
        print(f"User-Agent set to {user_agent}: {response}")
        return response


    async def reset_viewport(self) -> Dict:
        """Сбросить настройки вьюпорта."""
        response = await self.send_request("Emulation.clearDeviceMetricsOverride")
        print(f"Viewport reset: {response}")
        return response

    async def reset_geolocation(self) -> Dict:
        """Сбросить настройки геолокации."""
        response = await self.send_request("Emulation.clearGeolocationOverride")
        print(f"Geolocation reset: {response}")
        return response


    async def set_timezone_override(self, timezone_id: str) -> Dict:
        """
        Переопределить часовой пояс.

        Args:
            timezone_id: Идентификатор часового пояса (например, "Europe/Moscow")
        """
        response = await self.send_request("Emulation.setTimezoneOverride", {"timezoneId": timezone_id})
        print(f"Timezone set to {timezone_id}: {response}")
        return response

    async def wait_for_emulation_ready(self, timeout: float = 5.0) -> bool:
        """Дождаться применения всех настроек эмуляции."""
        start_time = time.time()
        print("Waiting for emulation to stabilize...")

        while time.time() - start_time < timeout:
            try:
                # Проверяем наличие ошибок
                response = await asyncio.wait_for(self.client.recv(), timeout=0.5)
                data = json.loads(response)

                if data.get("method") == "Emulation.virtualTimeBudgetExpired":
                    print("Virtual time budget expired!")
                    return False

            except asyncio.TimeoutError:
                # Если нет сообщений - считаем что эмуляция стабилизировалась
                print("Emulation stabilized")
                return True

        print("Emulation stabilization timeout")
        return False
