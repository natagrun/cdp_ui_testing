import asyncio
from asyncio import sleep

from new_main.driver.web_socket_client import WebSocketClient
from new_main.handlers.dom_handler import DOMHandler, logger
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
        # await emu_handler.enable_emulation()
        await dom_handler.enable_dom()
        # Переходим на страницу и ждем ее загрузку
        # await page_handler.navigate("https://demoqa.com")

        # Перезагружаем страницу
        # await page_handler.reload()

        await page_handler.navigate("https://demoqa.com/text-box")



        # element_data = await dom_handler.find_element_by_xpath("//button[@id='doubleClickBtn']")
        # logger.error(element_data)
        # await dom_handler.click_element(element_data)
        # await sleep(3)

        # Получить текст элемента по nodeId
        # text = await dom_handler.get_text(35)
        # print(text)
        # Получить текст элемента по селектору
        # text = await dom_handler.get_text_by_selector("#doubleClickBtn")
        # print(text)
        # element_data = await dom_handler.find_element_by_xpath("//button[@id='doubleClickBtn']")
        # element_data.__setattr__("nodeId",113)
        # text = await dom_handler.get_text_by_element(element_data)
        # print(text)
        #
        # element_cock = await dom_handler.find_element_by_xpath("//li[@id='item-0']")
        # await dom_handler.click_element(element_cock)
        # Кликаем с ожиданием навигации
        # success, new_url = await dom_handler.click_element(element_cock, wait_for_navigation=True)

        # if success:
        #     if new_url:
        #         print(f"Навигация произошла! Новый URL: {new_url}")
        #     else:
        #         print("Клик выполнен, но навигации не было")
        # else:
        #     print("Ошибка при клике")
        # text = await dom_handler.get_text_by_element(element_cock)
        # print(text)
        #
        # element_butt = await dom_handler.find_element_by_xpath("//button[@id='rightClickBtn']")
        # text = await dom_handler.get_text_by_element(element_butt)
        # print(text)
        # await dom_handler.click_element(element_butt)
        # await sleep(3)
        # await dom_handler.click_element(element_data)
        # await sleep(3)
        # await dom_handler.click_element(element_cock)

        text_input = await dom_handler.find_element_by_xpath("//*[@id='userName']")

        await dom_handler.insert_text(text_input,"Люблю маму")

        text_input2 = await dom_handler.find_element_by_xpath("//*[@id='userEmail']")

        await dom_handler.click_element(text_input2)

        text_input = await dom_handler.find_element_by_xpath("//*[@id='userName']")

        await dom_handler.click_element(text_input)

        text = await dom_handler.get_text_by_element(text_input)

        print(text)



        # Получить атрибуты элемента
        # attrs = await dom_handler.get_attributes(35)
        # if attrs:
        #     print(attrs.get("class"), attrs.get("type"))

        # Вариант 2 - комбинированный
        # success = await dom_handler.click_element_by_id("simpleLink")

        # await page_handler.reload()

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
