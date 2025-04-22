import asyncio
import logging
import time

from main.driver.web_socket_client import WebSocketClient, get_websocket_url
from main.handlers.dom_handler import DOMHandler
from main.handlers.navigation_handler import NavigationHandler
from main.handlers.page_handler import PageHandler
from main.objects.element import Element
from main.utils import assertions

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.ERROR,  # или logging.INFO — в зависимости от того, что хочешь видеть
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
)

async def test_websocket_connection():
    timerrr = time.time()
    websocket_client = WebSocketClient()

    # Получаем URL WebSocket через метод класса
    url = await get_websocket_url()
    if not url:
        print("Unable to find a WebSocket URL.")
        return

    # Устанавливаем URL для подключения
    websocket_client.url = url

    try:
        # Подключаемся к WebSocket
        await websocket_client.connect()
        page_handler = PageHandler(websocket_client)
        dom_handler = DOMHandler(websocket_client)
        await page_handler.enable_page()
        await dom_handler.enable_dom()

        # await page_handler.navigate("https://demoqa.com/alerts")
        #
        # print(time.strftime('%H:%M:%S'))
        # alert1test = await dom_handler.find_element_by_xpath("//button[@id='alertButton']")
        # await dom_handler.click_element(alert1test)
        # await dom_handler.is_alert_open()
        # # await sleep(3)
        #
        #
        # await page_handler.navigate("https://the-internet.herokuapp.com/javascript_alerts")
        # alert = await dom_handler.find_element_by_xpath("//button[@onclick=\"jsAlert()\"]")
        # while True:
        #     await dom_handler.click_element(alert)
        #     await dom_handler.is_alert_open()
        #     message = await dom_handler.find_element_by_xpath("//*[@id=\"result\"]")
        #     text = await dom_handler.get_text(message)
        #     print(text)

        await page_handler.navigate("https://store.steampowered.com")
        category = await dom_handler.find_element_by_xpath("//*[@id='genre_tab']")
        assertions.Assertions.assert_element_exists(category)
        await assertions.Assertions.assert_clickable(dom_handler, category.node_id)
        await assertions.Assertions.assert_text_contains(dom_handler,category,"Категории")
        # category.bind_handler(dom_handler)
        await category.move_mouse()

        rrr = await dom_handler.find_element_by_xpath(
            "//a[@class='popup_menu_item' and contains(text(), 'Рогалик')]")
        await assertions.Assertions.assert_visible(dom_handler, rrr.node_id)
        await assertions.Assertions.assert_clickable(dom_handler, rrr.node_id)

        # node_id = rrr.get("nodeId")
        # visible = await wait_for_condition(await dom_handler.is_element_visible(node_id=node_id),timeout=10,poll_frequency=2)
        await dom_handler.click_element(rrr)

        navigation_handler = NavigationHandler(websocket_client)
        await navigation_handler.navigate_back()
        await navigation_handler.navigate_forward()

        timerrww = time.time()
        print(timerrww - timerrr)
        print(await navigation_handler.get_current_url())
    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Закрываем WebSocket-соединение
        await websocket_client.close()


# Запуск основного теста
asyncio.run(test_websocket_connection())
