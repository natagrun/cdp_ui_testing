import asyncio
import time

import logging
from main.driver.driver import CdpDriver
from main.handlers.navigation_handler import NavigationHandler
from main.utils import assertions

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,  # или logging.INFO — в зависимости от того, что хочешь видеть
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
)

async def test_websocket_connection():
   global driver
   try:
        driver = CdpDriver()
        await driver.setup()
        await driver.page.navigate("https://store.steampowered.com")
        category = await driver.dom.find_element_by_xpath("//*[@id='genre_tab']")
        assertions.Assertions.assert_element_exists(category)
        await assertions.Assertions.assert_clickable(driver.dom, category.node_id)
        await assertions.Assertions.assert_text_contains(driver.dom,category,"Категории")
        # category.bind_handler(dom_handler)
        await category.move_mouse()

        rrr = await driver.dom.find_element_by_xpath(
            "//a[@class='popup_menu_item' and contains(text(), 'Рогалик')]")
        await assertions.Assertions.assert_visible(driver.dom, rrr.node_id)
        await assertions.Assertions.assert_clickable(driver.dom, rrr.node_id)

        # node_id = rrr.get("nodeId")
        # visible = await wait_for_condition(await dom_handler.is_element_visible(node_id=node_id),timeout=10,poll_frequency=2)
        await driver.dom.click_element(rrr)

        navigation_handler = NavigationHandler(driver.websocket_client)
        await navigation_handler.navigate_back()
        await navigation_handler.navigate_forward()

        timerrww = time.time()
        # print(timerrww - driver.timerrr)
        # print(await navigation_handler.get_current_url())
   except Exception as e:
       print(f"Error: {e}")
   finally:
        # Закрываем WebSocket-соединение
        await driver.teardown()


# Запуск основного теста
asyncio.run(test_websocket_connection())
