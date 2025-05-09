import asyncio

from main.driver.driver import CdpDriver
from main.utils import assertions


async def test_websocket_connection():
   try:
        async with CdpDriver() as driver:
            await driver.page.navigate("https://store.steampowered.com")

            category = await driver.dom.find_element_by_xpath("//*[@id='genre_tab']")
            assertions.Assertions.assert_element_exists(category)

            await assertions.Assertions.assert_clickable(driver.dom, category.node_id)
            await assertions.Assertions.assert_text_contains(driver.dom,category,"Категории")

            await category.move_mouse()

            rrr = await driver.dom.find_element_by_xpath(
                "//a[@class='popup_menu_item' and contains(text(), 'Рогалик')]")
            await assertions.Assertions.assert_visible(driver.dom, rrr.node_id)
            await assertions.Assertions.assert_clickable(driver.dom, rrr.node_id)
            await rrr.click()

            await driver.navigation.navigate_back()
            await driver.navigation.navigate_forward()

            search = await driver.dom.find_element_by_xpath("//input[@id='store_nav_search_term']")
            await search.insert_text("Миша гей")
            await search.clear()

   except Exception as e:
       print(f"Error: {e}")
   finally:
        # Закрываем WebSocket-соединение
        await driver.teardown()


# Запуск основного теста
asyncio.run(test_websocket_connection())
