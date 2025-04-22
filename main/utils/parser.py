import json
import logging
from typing import Union, Dict

logger = logging.getLogger(__name__)

async def parse_response(response: Union[str, Dict]) -> Dict:
    """
    Обрабатывает ответ от CDP: преобразует JSON-строку в словарь, либо возвращает словарь без изменений.

    :param response: Ответ от CDP (строка или словарь)
    :return: Словарь, полученный из JSON или исходный словарь. В случае ошибки — пустой словарь.
    """
    logger.debug(f"Разбор ответа. Тип данных: {type(response).__name__}")

    if isinstance(response, str):
        try:
            logger.debug("Попытка распарсить строку JSON в словарь")
            result = json.loads(response)
            logger.debug(f"Успешно распарсено: {result}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при разборе JSON: {e}")
            return {}

    logger.debug("Ответ уже является словарём — возврат без изменений")
    return response
