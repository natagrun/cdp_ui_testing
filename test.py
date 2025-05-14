import asyncio

from main.driver.driver import CdpDriver


async def test_websocket_connection():
   try:
        async with CdpDriver() as driver:
            await driver.page.navigate("http://127.0.0.1:5000")

            logger = driver.log
            dom = driver.dom  # DOMHandler
            assertor = driver.assertions  # Assertions

            logger.info("Тест: Проверка интерактивных элементов интерфейса")

            # 1. Нажать на тестовую кнопку
            button = await dom.find_element_by_xpath("//*[@id='button-trigger-event']","Кнопка1")
            await button.click()
            button_event_text = await dom.find_element_by_xpath("//*[@id='output-event-result']","Текст от кнопки1")
            await assertor.assert_element_text_equals(dom,button_event_text,"Кнопка нажата: событие зарегистрировано.")

            # 2. Ввести текст в поле ввода
            input_text = "Пример текста"
            input_field = await dom.find_element_by_xpath("//*[@id='input-text-data']","Поле для ввода")
            await input_field.insert_text(input_text)

            insert_button = await dom.find_element_by_xpath("//*[@id='button-show-input']","Кнопка2")
            await insert_button.click()

            insert_text_event = await dom.find_element_by_xpath("//*[@id='output-input-text']","Вывод текста поля")
            await assertor.assert_element_text_contains(dom,insert_text_event,input_text)


            # 4. Навести курсор на ссылку
            hover_link = await dom.find_element_by_xpath("//*[@id='hover-element-info']","Ссылка с hover-состоянием")
            await hover_link.move_mouse()
            hover_text = await dom.find_element_by_xpath("//*[@id='hover-tooltip-text']","hover-состояние")
            await assertor.assert_visible(dom,hover_text.node_id)
            await assertor.assert_text_contains(dom,hover_text,"Элемент hover успешно работает")

            # 5. Поставить галочку в чекбоксе
            checkbox = await dom.find_element_by_xpath("//*[@id='checkbox-consent']","Чекбокс")
            await checkbox.click()

            checkbox_text = await dom.find_element_by_xpath("//*[@id='output-checkbox-state']","Текст состояния чекбокса")
            await assertor.assert_element_text_contains(dom,checkbox_text,"Согласие подтверждено")

            # 6. Убрать галочку
            await checkbox.click()
            await assertor.assert_element_text_contains(dom, checkbox_text, "Согласие не получено.")

            logger.info("Тест успешно завершён")
            await driver.teardown()
   except Exception as e:

       print(f"Error: {e}")


# Запуск основного теста
asyncio.run(test_websocket_connection())
