# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import time
#
# # Инициализация драйвера
# driver = webdriver.Chrome()  # или любой другой драйвер
# wait = WebDriverWait(driver, 10)
#
# try:
#     timer1=time.time()
#     # Переходим на страницу
#     # driver.get("https://demoqa.com/text-box")
#     #
#     # # Работа с текстовыми полями
#     # text_input = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='userName']")))
#     # text_input.send_keys("Люблю маму")
#     #
#     # text_input2 = driver.find_element(By.XPATH, "//*[@id='userEmail']")
#     # text_input2.click()
#     #
#     # text_input.click()
#     # print(text_input.text)  # Получение текста элемента
#     #
#     # # Получение атрибутов элемента
#     # print(text_input.get_attribute("class"), text_input.get_attribute("type"))
#     #
#     # text_input2 = driver.find_element(By.XPATH, "//*[@id='userEmail']")
#     # text_input2.click()
#     #
#     # # Клик по элементу меню
#     # clicker = driver.find_element(By.XPATH, "(//*[@id='item-3'])[1]")
#     # clicker.click()
#     #
#     # # Удаление элементов
#     # delete_button = driver.find_element(By.XPATH, "//span[@title='Delete']")
#     # delete_button.click()# Удаление элементов
#     # delete_button = driver.find_element(By.XPATH, "//span[@title='Delete']")
#     # delete_button.click()# Удаление элементов
#     # delete_button = driver.find_element(By.XPATH, "//span[@title='Delete']")
#     # delete_button.click()
#     # # Добавление новой записи
#     # add_button = driver.find_element(By.XPATH, "//*[@id='addNewRecordButton']")
#     # add_button.click()
#     #
#     # # Заполнение формы
#     # fields = {
#     #     "firstName": "миша",
#     #     "lastName": "гей",
#     #     "userEmail": "mihunchik228@mail.ru",
#     #     "age": "14",
#     #     "salary": "6040405969",
#     #     "department": "Красивые мальчики"
#     # }
#     #
#     # for field_id, value in fields.items():
#     #     element = wait.until(EC.presence_of_element_located((By.ID, field_id)))
#     #     element.send_keys(value)
#     #
#     # # Отправка формы
#     # submit = driver.find_element(By.XPATH, "//button[@id='submit']")
#     # submit.click()
#
#     # Переходим на страницу Steam
#     print(time.strftime('%H:%M:%S'))
#     driver.get("https://store.steampowered.com/")
#
#     # Кликаем на ссылку "Новости"
#     news_link = wait.until(EC.element_to_be_clickable(
#         (By.XPATH, "//span[contains(text(),'Новости')]/parent::a")))
#     news_link.click()
#
#     # Кликаем на кнопку "Войти"
#     # Примечание: Steam может показывать разные формы входа, xpath может потребовать корректировки
#     sign_in_button = wait.until(EC.element_to_be_clickable(
#         (By.XPATH, "//button[contains(text(),'Войти')]")))
#     sign_in_button.click()
#     time.sleep(3)
#     # Вводим текст в поле ввода
#     # Примечание: Steam может показывать разные формы входа, xpath может потребовать корректировки
#     # name_input = wait.until(EC.element_to_be_clickable(
#     #     (By.XPATH, "//input[@type='text']")))
#     # name_input.send_keys("Миша гей")
#
#     # Кликаем на ссылку "бесплатный"
#     # Примечание: Steam может показывать разные элементы, xpath может потребовать корректировки
#     free_link = wait.until(EC.element_to_be_clickable(
#         (By.XPATH, "//a[contains(text(),'бесплатный')]")))
#     free_link.click()
#
#     timer2=time.time()
#
#
#     print(timer2-timer1)
#     # Пауза для демонстрации
#     time.sleep(3)
#
# finally:
#     # Закрытие браузера
#     driver.quit()