import time
from PyQt5 import QtGui
from typing import Optional, Tuple


class WeightDisplayController:
    """Управление отображением веса с оптимизированной производительностью"""

    def __init__(self, weight_label, status_label, font_family="DSEG7Classic-Regular"):
        self.weight_label = weight_label
        self.status_label = status_label
        self.font_family = font_family

        # Параметры отображения
        self.min_font_size = 22
        self.max_font_size = 42
        self.font_size_step = 4

        # Кэшированные стили для разных размеров шрифта
        self.font_styles_cache = {}
        self._init_font_styles()

        # Предыдущие значения для оптимизации
        self.last_weight_text = None
        self.last_font_size = self.max_font_size

        # Настройка метки веса
        self._setup_weight_label()

    def _init_font_styles(self):
        """Инициализирует кэш стилей шрифта для разных размеров"""
        base_style = "font-size: {}pt; background: transparent; border: none; margin-top: 15px; margin-left: 15px;"

        for size in range(self.min_font_size, self.max_font_size + 1, self.font_size_step):
            self.font_styles_cache[size] = base_style.format(size)

    def _setup_weight_label(self):
        """Настраивает метку веса для оптимального отображения"""
        if not self.weight_label:
            return

        try:
            # Устанавливаем начальный шрифт и стиль
            font = QtGui.QFont(self.font_family)
            self.weight_label.setFont(font)
            self.weight_label.setText("-")
            self.weight_label.setStyleSheet(self.font_styles_cache[self.max_font_size])
        except Exception:
            pass  # Игнорируем ошибки инициализации

    def update_weight(self, weight_value: float):
        """Обновляет отображение веса с оптимизацией производительности"""
        if not self._validate_weight_label():
            return

        try:
            # Проверяем, изменился ли вес
            weight_text = ".1f" if weight_value >= 0 else "-"

            # Выходим если значение не изменилось
            if weight_text == self.last_weight_text:
                return

            self.last_weight_text = weight_text

            # Определяем оптимальный размер шрифта
            optimal_font_size = self._calculate_font_size(weight_text)
            self._apply_font_size(optimal_font_size)

            # Обновляем текст
            self.weight_label.setText(weight_text)

        except Exception:
            # В случае ошибки устанавливаем дефолтное значение
            self._set_error_state()

    def _validate_weight_label(self) -> bool:
        """Проверяет валидность метки веса"""
        return (self.weight_label and
                hasattr(self.weight_label, 'setText') and
                hasattr(self.weight_label, 'setStyleSheet'))

    def _calculate_font_size(self, weight_text: str) -> int:
        """Вычисляет оптимальный размер шрифта для текста веса"""
        text_length = len(weight_text)

        if text_length <= 4:  # "1.0", "12.5"
            return self.max_font_size
        elif text_length <= 5:  # "123.4"
            return self.max_font_size - self.font_size_step
        elif text_length <= 6:  # "1234.5"
            return self.max_font_size - (self.font_size_step * 2)
        elif text_length <= 7:  # "12345.6"
            return self.max_font_size - (self.font_size_step * 3)
        elif text_length <= 8:  # "123456.7"
            return self.max_font_size - (self.font_size_step * 4)
        else:  # Очень большие значения
            return self.min_font_size

    def _apply_font_size(self, font_size: int):
        """Применяет размер шрифта с использованием кэша"""
        if font_size == self.last_font_size:
            return

        self.last_font_size = font_size

        try:
            cached_style = self.font_styles_cache.get(font_size)
            if cached_style:
                self.weight_label.setStyleSheet(cached_style)
        except Exception:
            pass  # Игнорируем ошибки применения стиля

    def _set_error_state(self):
        """Устанавливает состояние ошибки"""
        try:
            if self._validate_weight_label():
                self.weight_label.setText("-")
                self.weight_label.setStyleSheet(self.font_styles_cache[self.max_font_size])
                self.last_weight_text = None
        except Exception:
            pass

    def reset(self):
        """Сбрасывает состояние дисплея веса"""
        self.last_weight_text = None
        self.last_font_size = self.max_font_size
        self._set_error_state()

    def update_connection_status(self, is_connected: bool, port: Optional[str] = None, baud: Optional[int] = None):
        """Обновляет статус подключения"""
        try:
            if not self.status_label:
                return

            if is_connected and port:
                second_line = port
                if baud:
                    second_line = f"{second_line}, {baud}"
                text = f"Прием данных...Ок\n{second_line}"
            else:
                text = "Прием данных...None\n-"

            self.status_label.setText(text)
        except Exception:
            pass  # Игнорируем ошибки обновления статуса