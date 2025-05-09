#!/usr/bin/env python3
"""
Расширенный скрипт для запуска Chrome в режиме remote debugging
и выполнения множества тестовых файлов без ограничений через Python API.
Использует конфиг из cdp_driver.json (через Configurator).
"""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from main.driver.driver import Configurator


class ChromeTestRunner:
    def __init__(self, chrome_path, devtools_url):
        self.chrome_path = chrome_path
        self.devtools_url = devtools_url
        self.chrome_proc = None

    def start_chrome(self):
        parsed = urlparse(self.devtools_url)
        port = parsed.port or 9222
        print(f"Запуск Chrome: {self.chrome_path} --remote-debugging-port={port}")
        self.chrome_proc = subprocess.Popen([
            self.chrome_path,
            f"--remote-debugging-port={port}"
        ])

        print(f"Ожидание доступности DevTools по {self.devtools_url}...")
        for _ in range(10):
            try:
                with urllib.request.urlopen(self.devtools_url, timeout=1) as resp:
                    if resp.status == 200:
                        print("DevTools доступен.")
                        return
            except Exception:
                time.sleep(1)
        raise ConnectionError(f"Не удалось подключиться к DevTools по {self.devtools_url}")

    def stop_chrome(self):
        if self.chrome_proc:
            print("Завершение работы Chrome...")
            self.chrome_proc.terminate()
            self.chrome_proc.wait()

    def run_test(self, test_script):
        print(f"Запуск тестового скрипта: {test_script}")
        ret = subprocess.call([sys.executable, test_script])
        return ret

    def run_test(self, test_scripts):
        try:
            self.start_chrome()
            results = {}
            for test_script in test_scripts:
                ret_code = self.run_test(test_script)
                results[test_script] = ret_code
            return results
        finally:
            self.stop_chrome()

    def run_tests(*test_scripts):
        config = Configurator()
        chrome_path = config.chrome_path
        devtools_url = config.devtools_url

        runner = ChromeTestRunner(chrome_path, devtools_url)
        results = runner.run_test(test_scripts)

        for test, result in results.items():
            status = "OK" if result == 0 else f"FAILED (код {result})"
            print(f"Тест: {test} - результат: {status}")

    # Использование функции:
    run_tests('test1.py', 'test2.py', 'test3.py')


def main():
    if len(sys.argv) < 2:
        print("Использование: ./run_tests.py <путь_к_тесту1.py> [путь_к_тесту2.py ...]")
        sys.exit(1)

    test_scripts = sys.argv[1:]
    config = Configurator()
    chrome_path = config.chrome_path
    if not Path(chrome_path).exists():
        print(f"Chrome executable not found at {chrome_path}. "
              f"Укажите корректный путь в конфиге cdp_driver.json 'chrome.path'.")
        sys.exit(1)

    runner = ChromeTestRunner(chrome_path, config.devtools_url)
    results = runner.run_tests(test_scripts)

    print("\nРезультаты выполнения тестов:")
    for test, result in results.items():
        status = "OK" if result == 0 else f"FAILED (код {result})"
        print(f"- {test}: {status}")

    if any(code != 0 for code in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
