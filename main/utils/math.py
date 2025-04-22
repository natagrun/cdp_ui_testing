import logging
from typing import *

logger = logging.getLogger(__name__)

async def get_center_coordinates(model: Dict) -> Union[Tuple[float, float], bool]:
    """
    Вычисляет координаты центра DOM-элемента по его box-модели.

    :param model: Словарь с моделью элемента (box model)
    :return: Кортеж координат (x, y) или False в случае ошибки
    """
    if not model:
        logger.error("Box model data is missing")
        return False

    try:
        x = (model["content"][0] + model["content"][2]) / 2
        y = (model["content"][1] + model["content"][5]) / 2
        logger.debug(f"Center coordinates calculated: x={x}, y={y}")
        return x, y
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error calculating center coordinates: {e}")
        return False

