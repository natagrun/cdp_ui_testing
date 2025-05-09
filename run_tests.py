#!/usr/bin/env python3
"""
Скрипт для запуска Chrome в режиме remote debugging и выполнения тестового файла.
Использует конфиг из cdp_driver.json (через Configurator) для пути до Chrome и DevTools URL.

Использование:
 1. Сделать скрипт исполняемым: chmod +x run_tests.py
 2. Запустить тест: ./run_tests.py path/to/your_test.py

Если у вас нет команды python, можно явно вызвать python3:
  python3 run_tests.py path/to/your_test.py
"""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
import os

from main.driver.driver import Configurator


def main():
    if len(sys.argv) < 2:
        print("Использование: ./run_tests.py <путь_к_файлу_с_тестом.py>")
        sys.exit(1)

    test_script = sys.argv[1]
    config = Configurator()
    chrome_path = config.chrome_path
    if not Path(chrome_path).exists():
        print(f"Chrome не найден по пути: {chrome_path}. "
              f"Укажите корректный путь в конфиге cdp_driver.json 'chrome.path'.")
        sys.exit(1)

    parsed = urlparse(config.devtools_url)
    port = parsed.port or 9222

    # Создание временной директории для профиля Chrome
    user_data_dir = Path("./tmp/chrome-profile")
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Запуск Chrome: {chrome_path} --remote-debugging-port={port} --user-data-dir={user_data_dir}")
    chrome_proc = subprocess.Popen([
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir.resolve()}"
    ])

    print(f"Ожидание доступности DevTools по {config.devtools_url}...")
    for _ in range(10):
        try:
            with urllib.request.urlopen(config.devtools_url, timeout=1) as resp:
                if resp.status == 200:
                    print("DevTools доступен.")
                    break
        except Exception:
            time.sleep(1)
    else:
        print(f"Не удалось подключиться к DevTools по {config.devtools_url}")
        chrome_proc.terminate()
        sys.exit(1)

    print(f"Запуск тестового скрипта: {test_script}")
    ret = subprocess.call([sys.executable, test_script])

    print("Завершение работы Chrome...")
    chrome_proc.terminate()
    sys.exit(ret)


if __name__ == "__main__":
    main()
