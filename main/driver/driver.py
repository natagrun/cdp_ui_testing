import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional
import aiohttp

from main.driver.web_socket_client import WebSocketClient
from main.handlers.dom_handler import DOMHandler
from main.handlers.navigation_handler import NavigationHandler
from main.handlers.page_handler import PageHandler
from main.handlers.runtime_handler import RuntimeHandler
from main.utils.configurator import Configurator

def setup_logger(log_file: str, level: str = "INFO"):
    """
    Настраивает логгер с ротацией файлов.

    :param log_file: Путь до файла логов.
    :param level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    :return: Настроенный экземпляр Logger.
    """
    logger = logging.getLogger("cdp_ui")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Ротация: максимальный размер файла 10 МБ, хранить 5 старых копий
    handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )

    # Формат: время, уровень, имя логгера и сообщение
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

async def get_websocket_url(configurator: Configurator, logger) -> Optional[str]:
    """
    Получить WebSocket URL первой открытой страницы из DevTools.
    """
    url = configurator.devtools_url
    timeout = configurator.connect_timeout
    logger.info(f"Получение WebSocket URL из DevTools по {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    logger.error("Не удалось получить страницы из DevTools")
                    return None
                pages = await response.json()
                first = pages[0] if pages else {}
                ws = first.get("webSocketDebuggerUrl")
                logger.info(f"Найден URL: {ws}")
                return ws
    except Exception as e:
        logger.error(f"Ошибка при запросе DevTools: {e}")
        return None


class CdpDriver:
    _instance = None

    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(CdpDriver, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        if hasattr(self, "initialized") and self.initialized:
            return
        self.configurator = Configurator(config_path)
        self.websocket_client: Optional[WebSocketClient] = None
        self.page: Optional[PageHandler] = None
        self.dom: Optional[DOMHandler] = None
        self.navigation: Optional[NavigationHandler] = None
        self.runtime: Optional[RuntimeHandler] = None
        self.initialized = False
        self.log = setup_logger(
            log_file=self.configurator.logging_file or "cdp_ui.log",
            level=self.configurator.logging_level
        )

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.teardown()

    async def setup(self) -> bool:
        self.log.info("Инициализация CDP драйвера...")

        # Получение URL и создание WS-клиента
        source = self.configurator.websocket_url_source
        url = os.getenv("CDP_WEBSOCKET_URL") if source == "env" else await get_websocket_url(self.configurator,self.log)
        if not url:
            self.log.error("WebSocket URL не получен")
            return False

        self.websocket_client = WebSocketClient(
            url,
            connect_timeout=self.configurator.connect_timeout,
            retries=self.configurator.timeout("connect"),
            logger=self.log
        )
        try:
            await self.websocket_client.connect()
        except Exception:
            return False

        # Инициализация хендлеров
        self.page = PageHandler(self.websocket_client, self.log)
        self.dom = DOMHandler(self.websocket_client, self.log)
        self.navigation = NavigationHandler(self.websocket_client, self.log)
        self.runtime = RuntimeHandler(self.websocket_client, self.log)

        # Активация доменов
        try:
            await self.page.enable_page()
            await self.dom.enable_dom()
        except Exception as e:
            self.log.error(f"Ошибка активации CDP: {e}")
            await self.teardown()
            return False

        self.initialized = True
        self.log.info("CDP драйвер готов.")
        return True

    async def teardown(self) -> None:
        self.log.info("Завершение работы CDP драйвера...")
        if self.websocket_client:
            await self.websocket_client.close()
        self.websocket_client = None
        self.page = None
        self.dom = None
        self.navigation = None
        self.runtime = None
        self.initialized = False
        CdpDriver._instance = None
        self.log.info("Ресурсы освобождены.")
