import json
import logging
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import *

logger = logging.getLogger(__name__)


def _load_or_create(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        logger.info(f"Config file not found at {path}, creating default JSON config.")
        default = {
            "websocket_url_source": "auto",
            "devtools": {"url": "http://localhost:9222/json"},
            "timeouts": {"connect": 10, "command": 30},
            "logging": {"level": "INFO", "file": None}
        }
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _guess_chrome_path() -> str:
    """
    Предполагаемые пути до Chrome в зависимости от ОС. Возвращает первый найденный или первый в списке.
    """
    system = platform.system()
    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
    elif system == "Windows":
        pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        pf_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        candidates = [
            os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(pf_x86, "Google", "Chrome", "Application", "chrome.exe")
        ]
    else:
        candidates = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
    for path in candidates:
        if Path(path).exists():
            return path
    # если не найден, вернуть первый для дальнейшего сообщения
    return candidates[0]


class Configurator:
    """
    Загрузчик и провайдер конфигурации из JSON-файла, включая информацию об ОС и Chrome.
    """
    def __init__(self, path: Optional[str] = None):
        self.config_path = path or os.getenv("CDP_DRIVER_CONFIG", "cdp_driver.json")
        self._data = self._load_or_create(self.config_path)
        # Проверка пути до Chrome
        self._check_chrome_path()

    def _load_or_create(self, path: str) -> dict:
        p = Path(path)
        guessed = _guess_chrome_path()
        default = {
            "system": platform.system(),
            "chrome": {"path": guessed},
            "websocket_url_source": "auto",
            "devtools": {"url": "http://localhost:9222/json"},
            "timeouts": {"connect": 10, "command": 10,"inactivity":3},
            "logging": {"level": "INFO", "file": f"main/logs/logs_on_{datetime.now().strftime('%Y-%m-%d')}.log"}
        }
        if not p.exists():
            logger.info(f"Config not found at {path}, creating default JSON config.")
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=4)
            return default
        with open(p, "r", encoding="utf-8") as f:
            existing = json.load(f)

        merged = {**default, **existing}
        if "chrome" in existing:
            merged["chrome"]["path"] = existing["chrome"].get("path", guessed)
        return merged

    def _check_chrome_path(self) -> None:
        chrome_path = self.chrome_path
        if not Path(chrome_path).exists():
            logger.error(
                f"Предполагаемый путь до Chrome не найден: {chrome_path}. "
                "Пожалуйста, укажите корректный путь в конфиге 'chrome.path'."
            )
            raise FileNotFoundError(
                f"Chrome executable not found at {chrome_path}, add valid 'chrome.path' to config."
            )

    @property
    def system(self) -> str:
        return self._data.get("system", platform.system())

    @property
    def chrome_path(self) -> str:
        return self._data.get("chrome", {}).get("path", _guess_chrome_path())

    @property
    def websocket_url_source(self) -> str:
        return self._data.get("websocket_url_source", "auto")

    @property
    def devtools_url(self) -> str:
        return self._data.get("devtools", {}).get("url", "http://localhost:9222/json")

    def timeout(self, name: str) -> int:
        return int(self._data.get("timeouts", {}).get(name, 0))

    @property
    def connect_timeout(self) -> int:
        return self.timeout("connect")

    @property
    def command_timeout(self) -> int:
        return self.timeout("command")

    @property
    def inactivity_timeout(self) -> int:
        return self.timeout("inactivity")

    @property
    def logging_level(self) -> str:
        return self._data.get("logging", {}).get("level", "INFO")

    @property
    def logging_file(self) -> Optional[str]:
        return self._data.get("logging", {}).get("file")

