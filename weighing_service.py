import logging
from datetime import datetime
from logger import get_logger

# Настройка логирования для weighing_service модуля
logger = get_logger('weighing_service')
from typing import Optional, Dict, Any
from database import save_weighing


class WeighingService:
    """Сервис для бизнес-логики взвешивания"""

    def __init__(self):
        pass

    def save_manual_weighing(self,
                           weight: float,
                           operator: str,
                           cargo_name: str = '-',
                           sender: str = '-',
                           recipient: str = '-',
                           comment: str = '-',
                           scales_name: str = '-') -> bool:
        """
        Сохранить ручное взвешивание

        Args:
            weight: Вес в кг
            operator: Оператор
            cargo_name: Наименование груза
            sender: Отправитель
            recipient: Получатель
            comment: Примечание
            scales_name: Название весов

        Returns:
            bool: True если сохранение успешно
        """
        if not self._validate_weighing_data(weight, operator):
            return False

        try:
            current_datetime = datetime.now().strftime("%d.%m.%Y %H:%M")

            save_weighing(
                datetime_str=current_datetime,
                weight=weight,
                operator=operator,
                weighing_mode='Ручное',
                cargo_name=cargo_name,
                sender=sender,
                recipient=recipient,
                comment=comment,
                scales_name=scales_name
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении ручного взвешивания: {str(e)}")
            return False

    def _validate_weighing_data(self, weight: float, operator: str) -> bool:
        """Проверить корректность данных взвешивания"""
        if not isinstance(weight, (int, float)) or weight <= 0:
            return False

        if not operator or not operator.strip():
            return False

        return True

    def get_weighing_data_template(self, current_weight: float, operator: str, scales_name: str = '-') -> Dict[str, Any]:
        """Получить шаблон данных для взвешивания"""
        return {
            'weight': current_weight,
            'operator': operator,
            'cargo_name': '-',
            'sender': '-',
            'recipient': '-',
            'comment': '-',
            'scales_name': scales_name
        }