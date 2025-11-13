import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from database import save_weighing


class AutoWeighingEngine:
    """Движок автоматического взвешивания с логикой стабилизации веса"""

    def __init__(self, user: Optional[str] = None, scales_name: Optional[str] = None):
        self.user = user
        self.scales_name = scales_name

        # Переменные для автоматического взвешивания
        self.last_weight: Optional[float] = None
        self.last_weight_time: Optional[float] = None
        self.stable_weight_duration: float = 0.0
        self.last_saved_weight: Optional[float] = None
        self.weight_was_zero: bool = True  # Флаг, что вес был сброшен на ноль

        # Настройки автоматического взвешивания
        self.min_weight_threshold: float = 0.1  # Минимальный вес для срабатывания (кг)
        self.max_weight_threshold: float = 100000  # Максимальный вес для предотвращения ошибок (кг)
        self.auto_save_timeout: float = 30.0  # Таймаут для автоматического сохранения (секунды)
        self.stabilization_interval: int = 3  # Интервал стабилизации в секундах

    def set_user(self, user: str):
        """Установить текущего пользователя"""
        self.user = user

    def set_scales_name(self, scales_name: str):
        """Установить название весов"""
        self.scales_name = scales_name

    def set_stabilization_interval(self, interval: int):
        """Установить интервал стабилизации в секундах"""
        self.stabilization_interval = max(1, min(30, interval))  # Ограничение 1-30 секунд

    def reset_state(self):
        """Сбросить состояние автоматического взвешивания"""
        self.weight_was_zero = True
        self.last_weight = None
        self.last_weight_time = None
        self.stable_weight_duration = 0

    def process_weight(self, current_weight: float) -> Tuple[bool, Optional[str]]:
        """
        Обработать новый вес и определить необходимость автосохранения

        Returns:
            Tuple[bool, Optional[str]]: (нужно ли сохранить, сообщение о статусе)
        """
        if not self._validate_auto_save_conditions(current_weight):
            return False, None

        current_time = time.time()

        # Если вес равен нулю, устанавливаем флаг сброса
        if current_weight == 0:
            self._handle_zero_weight()
            return False, None

        # Если вес не был сброшен на ноль после последнего сохранения, игнорируем
        if not self.weight_was_zero and self.last_saved_weight is not None:
            return False, None

        # Обновляем состояние стабильности веса
        weight_changed = self._update_weight_stability(current_weight, current_time)

        # Проверяем условия для автосохранения
        if self._should_auto_save(current_weight, current_time):
            self._perform_auto_save(current_weight)
            return True, f"Автоматически сохранен вес: {current_weight:.2f} кг"

        return False, None

    def _validate_auto_save_conditions(self, weight: float) -> bool:
        """Проверить базовые условия для автосохранения"""
        if not isinstance(weight, (int, float)) or weight < 0:
            return False

        if not self.user:
            return False

        if weight < self.min_weight_threshold or weight > self.max_weight_threshold:
            return False

        return True

    def _handle_zero_weight(self):
        """Обработать нулевой вес"""
        self.weight_was_zero = True
        self.last_weight = None
        self.last_weight_time = None
        self.stable_weight_duration = 0

    def _update_weight_stability(self, current_weight: float, current_time: float) -> bool:
        """
        Обновить состояние стабильности веса

        Returns:
            bool: True если вес изменился
        """
        weight_changed = False

        # Если это новый вес или вес изменился
        if self.last_weight != current_weight:
            self.last_weight = current_weight
            self.last_weight_time = current_time
            self.stable_weight_duration = 0
            weight_changed = True
        else:
            # Вес не изменился, увеличиваем время стабилизации
            if self.last_weight_time is not None:
                self.stable_weight_duration = current_time - self.last_weight_time

        return weight_changed

    def _should_auto_save(self, weight: float, current_time: float) -> bool:
        """Определить, нужно ли выполнять автосохранение"""
        # Вес должен быть стабилен в течение заданного интервала
        # и больше нуля, и должен был быть сброшен на ноль перед этим
        return (self.stable_weight_duration >= self.stabilization_interval and
                weight > 0 and
                self.weight_was_zero)

    def _perform_auto_save(self, weight: float):
        """Выполнить автоматическое сохранение веса"""
        try:
            # Получить текущую дату и время
            current_datetime = datetime.now().strftime("%d.%m.%Y %H:%M")

            # Данные для сохранения (по умолчанию)
            weighing_data = {
                'datetime_str': current_datetime,
                'weight': weight,
                'operator': self.user,
                'weighing_mode': 'Автоматическое',
                'cargo_name': '-',
                'sender': '-',
                'recipient': '-',
                'comment': '-',
                'scales_name': self.scales_name or '-'
            }

            # Сохранить в базу данных
            save_weighing(**weighing_data)

            # Обновить состояние
            self.last_saved_weight = weight
            self.weight_was_zero = False

        except Exception as e:
            print(f"Ошибка при автоматическом сохранении: {str(e)}")
            raise

    def get_status_info(self) -> Dict[str, Any]:
        """Получить информацию о текущем состоянии"""
        return {
            'last_weight': self.last_weight,
            'stable_duration': self.stable_weight_duration,
            'stabilization_interval': self.stabilization_interval,
            'weight_was_zero': self.weight_was_zero,
            'last_saved_weight': self.last_saved_weight,
            'auto_enabled': True  # Всегда включено если объект существует
        }