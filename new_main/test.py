import asyncio
import time
from asyncio import sleep

from pyppeteer.chromium_downloader import download_zip

from new_main.driver.web_socket_client import WebSocketClient
from new_main.handlers.dom_handler import DOMHandler, logger
from new_main.handlers.element_handler import ElementHandler
from new_main.handlers.emulation_handler import EmulationHandler
from new_main.handlers.page_handler import PageHandler

async def test_websocket_connection():
    timerrr = time.time()
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

        # Создаем обработчик для работы с DOM
        dom_handler = DOMHandler(websocket_client)
        element_handler = ElementHandler(dom_handler)

        # asyncio.create_task(listen_messages(dom_handler))
        # Активируем протокол Page
        await page_handler.enable_page()
        # dom_handler.request_id += 1
        # await emu_handler.enable_emulation()
        await dom_handler.enable_dom()
        # Переходим на страницу и ждем ее загрузку
        # await page_handler.navigate("https://demoqa.com")

        # Перезагружаем страницу
        # await page_handler.reload()

        # await page_handler.navigate("https://store.steampowered.com/")
        #
        # cat = await dom_handler.find_element_by_xpath("//a[contains(text(),'Категории')]")
        # await dom_handler.move_mouse_on_element(cat)
        #
        # await page_handler.wait_for_page_dom_load(5,2)
        # # await asyncio.sleep(3)
        # sign = await dom_handler.find_element_by_xpath("//*[contains(text(),'Категории')]"
        #                                                "//ancestor-or-self::*//a[contains(text(),'Рогалик')]")
        # await dom_handler.click_element(sign)
        # logo = await dom_handler.find_element_by_xpath("//div[@class='logo']")
        #
        # while True:
        #
        #     await dom_handler.click_element(logo)
        #
        #     await dom_handler.move_mouse_on_element(cat)
        #     await page_handler.wait_for_page_dom_load(5, 2)
        #
        #     await dom_handler.click_element(sign)
        # name = await dom_handler.find_element_by_xpath("//input[@type='text']")
        # # await dom_handler.click_element(name)
        # await dom_handler.insert_text(name,"Миша гей")



        # sign2 = await dom_handler.find_element_by_xpath("//a[contains(text(),'бесплатный')]")
        # await dom_handler.click_element(sign2)



        # while True:
        #     print(time.strftime('%H:%M:%S'))
        #     await websocket_client.receive_message()



        # text_input = await dom_handler.find_element_by_xpath("//*[@id='userName']")
        #
        # await dom_handler.insert_text(text_input,"Люблю маму")
        #
        # text_input2 = await dom_handler.find_element_by_xpath("//*[@id='userEmail']")
        #
        # await dom_handler.click_element(text_input2)
        #
        # text_input = await dom_handler.find_element_by_xpath("//*[@id='userName']")
        #
        # await dom_handler.click_element(text_input)
        #
        # text = await dom_handler.get_text_by_element(text_input)
        #
        # print(text)
        #
        #
        #
        # # Получить атрибуты элемента
        # attrs = await dom_handler.get_attributes(text_input)
        # if attrs:
        #     print(attrs.get("class"), attrs.get("type"))

        # text_input = await dom_handler.find_element_by_xpath("//*[@id='userEmail']")
        # await dom_handler.focus_on_element(text_input)
        #

        #
        #
        # add_b = await dom_handler.find_element_by_xpath("//*[@id='addNewRecordButton']")

        # await dom_handler.click_element(add_b)
        #
        #
        # name = await dom_handler.find_element_by_xpath("//*[@id='firstName']")
        #
        # await dom_handler.insert_text(name,"миша")
        #
        # last_name = await dom_handler.find_element_by_xpath("//*[@id='lastName']")
        #
        # await dom_handler.insert_text(last_name,"гей")
        #
        # email = await dom_handler.find_element_by_xpath("//*[@id='userEmail']")
        #
        # await dom_handler.insert_text(email,"mihunchik228@mail.ru")
        #
        # age = await dom_handler.find_element_by_xpath("//*[@id='age']")
        #
        # await dom_handler.insert_text(age,"14")
        #
        # salary = await dom_handler.find_element_by_xpath("//*[@id='salary']")
        #
        # await dom_handler.insert_text(salary,"6040405969")
        #
        # department = await dom_handler.find_element_by_xpath("//*[@id='department']")
        #
        # await dom_handler.insert_text(department,"Красивые мальчики")
        #
        # submit = await dom_handler.find_element_by_xpath("//button[@id='submit']")
        #
        # await dom_handler.click_element(submit)
        #
        #



        await page_handler.navigate("https://demoqa.com/alerts")
        # await dom_handler.start_dialog_listener(accept=True)

        print(time.strftime('%H:%M:%S'))



        alert1test = await dom_handler.find_element_by_xpath("//button[@id='alertButton']")
        # await dom_handler.enable_alert_monitoring()
        await dom_handler.click_element(alert1test)
        await dom_handler.is_alert_open()
        await sleep(3)

        clicker = await dom_handler.find_element_by_xpath("//*[@id='confirmButton']")
        await dom_handler.click_element(clicker)

        # delete_last_node = await dom_handler.find_element_by_xpath("//span[@title='Delete']")
        # await dom_handler.click_element(delete_last_node)
        # await dom_handler.click_element(delete_last_node)
        # await dom_handler.click_element(delete_last_node)
        # while True:
        #     print(time.strftime('%H:%M:%S'))
        #     await websocket_client.receive_message()



        # await dom_handler.click_element(clicker,True)
        # start_time = time.time()


        # response = await asyncio.wait_for(websocket_client.receive_message(), timeout=5)



        # while True:
        #     response = await websocket_client.receive_message()
        #     print(time.strftime('%H:%M:%S'))
        #     # print(response)

        # print(1)
        # print(button)

        # await dom_handler.get_attributes(button)
        # await page_handler.get_layout_metrics()

        # Останавливаем загрузку страницы
        # await page_handler.stop_loading()

        # Добавляем скрипт, который будет выполняться при загрузке каждой новой страницы
        # await page_handler.add_script_to_evaluate_on_new_document("console.log('Script loaded!');")
        timerrww = time.time()

        print(timerrww-timerrr)
    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Закрываем WebSocket-соединение
        await websocket_client.close()


# Запуск основного теста
asyncio.run(test_websocket_connection())
