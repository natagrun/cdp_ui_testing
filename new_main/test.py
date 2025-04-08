import asyncio
from time import sleep

import websockets
import json
import aiohttp
import base64


from new_main.driver.web_socket_client import WebSocketClient
from new_main.handlers.base_handler import BaseHandler
from new_main.handlers.dom_handler import DOMHandler
from new_main.handlers.element_handler import ElementHandler
from new_main.handlers.emulation_handler import EmulationHandler
from new_main.handlers.page_handler import PageHandler


async def test_websocket_connection():
    websocket_client = WebSocketClient()

    # Получаем URL WebSocket через метод класса
    url = await websocket_client.get_websocket_url()
    if not url:
        print("Unable to find a WebSocket URL.")
        return

    # Устанавливаем URL для подключения
    websocket_client.url = url

    try:
        # Подключаемся к WebSocket
        await websocket_client.connect()

        # Создаем обработчик для работы с Page
        page_handler = PageHandler(websocket_client)
        # Создаем обработчик для работы с Emulation
        emu_handler = EmulationHandler(websocket_client)
        # Создаем обработчик для работы с DOM
        dom_handler = DOMHandler(websocket_client)
        element_handler = ElementHandler(dom_handler)

        # Активируем протокол Page
        await page_handler.enable_page()
        await emu_handler.enable_emulation()
        await dom_handler.enable_dom()
        # Переходим на страницу и ждем ее загрузку
        # await page_handler.navigate("https://demoqa.com")

        # Перезагружаем страницу
        # await page_handler.reload()

        await page_handler.navigate("https://demoqa.com/links")
        # await page_handler.navigate("https://chatgptchatapp.com/")
        # Перезагружаем страницу

        # await page_handler.reload()
        #
        # await emu_handler.set_viewport_size(600,600)
        # await page_handler.reload()
        # sleep(5)
        # await emu_handler.reset_viewport()
        # await page_handler.reload()
        # sleep(5)
        # Делаем скриншот страницы
        # await page_handler.capture_screenshot()
        # sleep(3)

        # document = await dom_handler.get_document()
        # # print(1)
        # root= json.loads(document)
        # root_id = root['result']['root']['nodeId']
        # print(root_id)
        # print(1)
        # Ищем кнопку по XPath
        # await dom_handler.query_selector_xpath(xpath="//input[@type='radio']")

        await dom_handler.enable_dom()

        element_data = await dom_handler.find_element_by_id("simpleLink")
        if element_data:
            await dom_handler.click_element(element_data)

        # Вариант 2 - комбинированный
        # success = await dom_handler.click_element_by_id("simpleLink")

        await page_handler.reload()

        # print(1)
        # print(button)

        # await dom_handler.get_attributes(button)
        # await page_handler.get_layout_metrics()

        # Останавливаем загрузку страницы
        # await page_handler.stop_loading()

        # Добавляем скрипт, который будет выполняться при загрузке каждой новой страницы
        # await page_handler.add_script_to_evaluate_on_new_document("console.log('Script loaded!');")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Закрываем WebSocket-соединение
        await websocket_client.close()


# Запуск основного теста
asyncio.run(test_websocket_connection())
