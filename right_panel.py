import sqlite3
import re
import time
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui
import serial  # pyserial, установить через pip install pyserial
from database import save_weighing


DB_FILE = 'weights_journal.db'


class WeightDisplayManager:
    """Управление отображением веса с оптимизированной производительностью"""

    def __init__(self, weight_label, status_label, font_family="Arial"):
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
        base_style = f"font-size: {{}}pt; background: transparent; border: none; margin-top: 15px; margin-left: 15px;"

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

    def update_weight(self, weight_value):
        """Обновляет отображение веса с оптимизацией производительности"""
        if not self._validate_weight_label():
            return

        try:
            # Проверяем, изменился ли вес
            weight_text = f"{weight_value:.1f}" if weight_value >= 0 else "-"

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

    def _validate_weight_label(self):
        """Проверяет валидность метки веса"""
        return (self.weight_label and
                hasattr(self.weight_label, 'setText') and
                hasattr(self.weight_label, 'setStyleSheet'))

    def _calculate_font_size(self, weight_text):
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

    def _apply_font_size(self, font_size):
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

    def update_connection_status(self, is_connected, port=None, baud=None):
        """Обновляет статус подключения"""
        try:
            if not self.status_label:
                return

            if is_connected and port:
                second_line = f"{port}"
                if baud:
                    second_line = f"{second_line}, {baud}"
                text = f"Прием данных...Ок\n{second_line}"
            else:
                text = "Прием данных...None\n-"

            self.status_label.setText(text)
        except Exception:
            pass  # Игнорируем ошибки обновления статуса


class RightPanelWidget(QtWidgets.QWidget):
    # Сигнал для уведомления о новом взвешивании
    weighing_saved = QtCore.pyqtSignal()
    # Сигнал для удаления блока весов
    delete_requested = QtCore.pyqtSignal()

    def __init__(self, font_family="Arial", parent=None, current_user=None, scales_number=1, show_info_block=True):
        super().__init__(parent)
        self.current_user = current_user
        self.serial_port = None
        self.current_config_name = None
        self.current_protocol = 1  # Протокол по умолчанию
        self.setFixedWidth(437)
        self.setStyleSheet("background-color: #f9fafb; font-size: 10pt;")
        self.show_info_block = show_info_block

        # Переменные для автоматического взвешивания
        self.last_weight = None
        self.last_weight_time = None
        self.stable_weight_duration = 0.0
        self.last_saved_weight = None
        self.weight_was_zero = True  # Флаг, что вес был сброшен на ноль


        # Оптимизация обновления интерфейса
        self.last_ui_update = 0.0
        self.ui_update_interval = 100  # Обновляем интерфейс раз в 100мс для баланса производительности

        # Убираем старую переменную для статуса веса - теперь в WeightDisplayManager

        # Оптимизация автоматического взвешивания
        self.last_auto_weigh_call = 0.0
        self.auto_weigh_interval = 100  # Интервал вызовов автоматического взвешивания (мс) для более быстрой реакции

        # Дополнительные настройки автоматического взвешивания
        self.min_weight_threshold = 0.1  # Минимальный вес для срабатывания (кг)
        self.max_weight_threshold = 100000  # Максимальный вес для предотвращения ошибок (кг)
        self.auto_save_timeout = 30.0  # Таймаут для автоматического сохранения (секунды)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(15)

        # Информация о взвешивании (только для первого блока весов)
        if self.show_info_block:
            self.info_block = QtWidgets.QWidget()
            info_layout = QtWidgets.QVBoxLayout(self.info_block)
            info_layout.setContentsMargins(8, 8, 8, 8)
            info_layout.setSpacing(4)
            self.info_block.setStyleSheet("background: transparent;")

            label_info_title = QtWidgets.QLabel("ИНФОРМАЦИЯ О ВЗВЕШИВАНИИ")
            label_info_title.setStyleSheet("font-weight: bold; margin-bottom: 6px;")
            info_layout.addWidget(label_info_title)

            self.label_datetime = QtWidgets.QLabel("")
            info_layout.addWidget(self.label_datetime)

            self.label_operator = QtWidgets.QLabel("")
            info_layout.addWidget(self.label_operator)

            layout.addWidget(self.info_block)

        # Объединенный контейнер "Весы" для остальных блоков
        main_block = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(main_block)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        main_block.setStyleSheet("""
            background: transparent;
            border: 1px solid #9ca3af;
            border-radius: 8px;
        """)

        # Заголовок для объединенного блока с кнопкой удаления
        title_widget = QtWidgets.QWidget()
        title_widget.setStyleSheet("background: transparent; border: none;")
        title_layout = QtWidgets.QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)

        scales_title = QtWidgets.QLabel(f"Весы№{scales_number}")
        scales_title.setStyleSheet("font-weight: bold; font-size: 12pt; background: transparent; border: none; margin-bottom: 5px;")
        title_layout.addWidget(scales_title)

        # Кнопка удаления (крестик) - показываем только если это не первый блок весов
        if scales_number > 1:
            delete_button = QtWidgets.QPushButton("×")
            delete_button.setFixedSize(20, 20)
            # Центрируем текст в кнопке
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-family: "Courier New", monospace;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                    text-align: center;
                    line-height: 20px;
                }
                QPushButton:hover {
                    background-color: #b91c1c;
                }
            """)
            delete_button.setToolTip("Удалить весы")
            delete_button.clicked.connect(self.delete_requested.emit)
            title_layout.addWidget(delete_button)

        title_layout.addStretch()
        main_layout.addWidget(title_widget)

        # Конфигурация с выпадающим меню и кнопками
        config_block = QtWidgets.QWidget()
        config_layout = QtWidgets.QVBoxLayout(config_block)
        config_layout.setContentsMargins(8, 8, 8, 8)
        config_layout.setSpacing(6)
        config_block.setStyleSheet("border: 1px solid #9ca3af; border-radius: 6px;")

        connect_title = QtWidgets.QLabel("Подключение к весам")
        connect_title.setStyleSheet("font-weight: bold; font-size: 11pt; background: transparent; border: none;")
        config_layout.addWidget(connect_title)

        ctrl_layout = QtWidgets.QHBoxLayout()
        ctrl_layout.setSpacing(10)

        self.config_combo = QtWidgets.QComboBox()
        self.config_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #9ca3af;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 10pt;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #6b7280;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #9ca3af;
                border-radius: 4px;
                selection-background-color: #dbeafe;
                selection-color: #1f2937;
                outline: none;
                padding: 5px;
            }
            QComboBox QAbstractItemView::item {
                padding: 5px 10px;
                margin: 0;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #f3f4f6;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #dbeafe;
                color: #1f2937;
            }
        """)
        ctrl_layout.addWidget(self.config_combo)

        self.connect_button = QtWidgets.QPushButton("Подключить")
        self.connect_button.setStyleSheet(
            "background-color: #e5e7eb; border: 1px solid #9ca3af; padding: 4px 10px; font-size: 10pt;"
        )
        ctrl_layout.addWidget(self.connect_button)

        self.disconnect_button = QtWidgets.QPushButton("Отключить")
        self.disconnect_button.setStyleSheet(
            "background-color: #e5e7eb; border: 1px solid #9ca3af; padding: 4px 10px; font-size: 10pt;"
        )
        ctrl_layout.addWidget(self.disconnect_button)

        config_layout.addLayout(ctrl_layout)
        main_layout.addWidget(config_block)

        # Блок с весом
        self.weight_block = QtWidgets.QWidget()
        self.weight_block.setFixedHeight(160)  # Увеличенная высота блока веса для полного отображения цифр
        self.weight_layout = QtWidgets.QVBoxLayout(self.weight_block)
        self.weight_layout.setContentsMargins(12, 12, 12, 12)
        self.weight_layout.setSpacing(4)
        self.weight_block.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                         stop:0 rgba(254,250,224,255),
                                         stop:1 rgba(255,255,240,255));
            border: 1px solid black;
            border-radius: 15px;
        """)

        # Верхняя строка с весом и единицей измерения
        weight_row = QtWidgets.QWidget()
        weight_row_layout = QtWidgets.QHBoxLayout(weight_row)
        weight_row_layout.setContentsMargins(0, 0, 0, 0)
        weight_row.setStyleSheet("background: transparent; border: none;")

        self.weight_label = QtWidgets.QLabel("-")
        self.status_label = QtWidgets.QLabel("Прием данных...None\n-")
        self.status_label.setStyleSheet("font-family: Arial, sans-serif; font-size: 11pt; color: #0030df;")

        unit_label = QtWidgets.QLabel("kg")
        unit_label.setStyleSheet("""
            font-family: Arial, sans-serif;
            font-weight: normal;
            font-size: 28pt;
            color: #222222;
        """)
        unit_label.setContentsMargins(0, 0, 0, 0)

        weight_row_layout.addWidget(self.weight_label)
        weight_row_layout.addWidget(unit_label)
        weight_row_layout.addStretch()

        # Добавляем строки в layout блока веса
        self.weight_layout.addWidget(weight_row)

        # Нижняя строка с двумя надписями внутри блока веса
        bottom_row = QtWidgets.QWidget()
        bottom_row_layout = QtWidgets.QHBoxLayout(bottom_row)
        bottom_row_layout.setContentsMargins(0, 0, 0, 0)
        bottom_row_layout.setSpacing(8)
        bottom_row.setStyleSheet("background: transparent; border: none; margin-top: 12px;")

        self.auto_weight_label = QtWidgets.QLabel("Автоматическое взвешивание\nвключено")
        self.auto_weight_label.setStyleSheet("font-family: Arial, sans-serif; font-size: 11pt; color: #0030df; margin-left: 12px;")

        bottom_row_layout.addWidget(self.status_label)
        bottom_row_layout.addWidget(self.auto_weight_label)
        self.weight_layout.addWidget(bottom_row)

        # Добавляем объединенный блок в основной layout
        main_layout.addWidget(self.weight_block)

        # Горизонтальный блок с кнопкой "Сохранить вес" слева и автоматическим взвешиванием справа
        control_block = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_block)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(20)
        control_block.setStyleSheet("background: transparent; border: none;")

        # Левая часть - кнопка "Сохранить вес"
        left_control_block = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_control_block)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.save_weight_button = QtWidgets.QPushButton("Сохранить вес")
        icon = QtGui.QIcon("static/sint.svg")
        self.save_weight_button.setIcon(icon)
        self.save_weight_button.setStyleSheet("""
            background-color: #e5e7eb;
            border: 1px solid #9ca3af;
            padding: 6px 12px;
            font-size: 12pt;
            border-radius: 6px;
            margin-right: 12px;
            margin-top: 0px;
        """)
        left_layout.addWidget(self.save_weight_button)
        left_layout.addStretch()

        # Правая часть - блок автоматического взвешивания
        auto_weight_block = QtWidgets.QWidget()
        auto_weight_layout = QtWidgets.QVBoxLayout(auto_weight_block)
        auto_weight_layout.setContentsMargins(0, 0, 0, 0)
        auto_weight_layout.setSpacing(6)

        auto_weight_title = QtWidgets.QLabel("Автоматическое взвешивание")
        auto_weight_title.setStyleSheet("font-weight: bold; font-size: 10pt; background: transparent;")
        auto_weight_layout.addWidget(auto_weight_title)

        checkbox_layout = QtWidgets.QVBoxLayout()
        checkbox_layout.setSpacing(4)

        self.auto_weight_checkbox = QtWidgets.QCheckBox("Включить")
        checkbox_layout.addWidget(self.auto_weight_checkbox)

        interval_label = QtWidgets.QLabel("Интервал стабилизации в сек:")
        checkbox_layout.addWidget(interval_label)

        self.interval_input = QtWidgets.QLineEdit()
        self.interval_input.setFixedWidth(50)
        self.interval_input.setText("3")  # Увеличиваем интервал по умолчанию до 3 секунд
        self.interval_input.setStyleSheet(
            "padding: 5px; border: 1px solid #9ca3af; border-radius: 4px; background: white; font-size: 10pt;")
        # Добавляем валидатор для интервала стабилизации (1-30 секунд)
        validator = QtGui.QIntValidator(1, 30, self.interval_input)
        self.interval_input.setValidator(validator)
        checkbox_layout.addWidget(self.interval_input)


        checkbox_layout.addStretch()
        auto_weight_layout.addLayout(checkbox_layout)

        # Добавляем левую и правую части в горизонтальный layout
        control_layout.addWidget(left_control_block)
        control_layout.addWidget(auto_weight_block)
        main_layout.addWidget(control_block)

        # Блок дополнительной информации с полями ввода (collapsible)
        extra_block = QtWidgets.QWidget()
        extra_layout = QtWidgets.QVBoxLayout(extra_block)
        extra_layout.setContentsMargins(8, 8, 8, 8)
        extra_layout.setSpacing(4)
        extra_block.setStyleSheet("background: transparent;")

        # Заголовок с кнопкой для сворачивания/разворачивания
        header_widget = QtWidgets.QWidget()
        header_widget.setStyleSheet("background: transparent; border: none;")
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        label_extra_title = QtWidgets.QLabel("ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ")
        label_extra_title.setStyleSheet("font-weight: bold; margin-bottom: 0px;")

        self.toggle_button = QtWidgets.QPushButton("▼")
        self.toggle_button.setFixedSize(25, 25)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #e5e7eb;
                border: none;
                border-radius: 3px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d1d5db;
            }
        """)
        self.toggle_button.setToolTip("Развернуть/свернуть поля ввода")

        header_layout.addWidget(label_extra_title)
        header_layout.addWidget(self.toggle_button)
        header_layout.addStretch()

        # Контейнер для полей ввода
        self.fields_container = QtWidgets.QWidget()
        self.fields_container.setStyleSheet("background: transparent; border: none;")
        fields_layout = QtWidgets.QFormLayout(self.fields_container)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(4)

        self.input_cargo_name = QtWidgets.QLineEdit()
        self.input_sender = QtWidgets.QLineEdit()
        self.input_recipient = QtWidgets.QLineEdit()
        self.input_comment = QtWidgets.QTextEdit()
        self.input_comment.setFixedHeight(60)

        # Стилизация полей ввода
        line_edit_style = """
            padding: 5px;
            border: 1px solid #9ca3af;
            border-radius: 4px;
            background: white;
            font-size: 10pt;
        """
        self.input_cargo_name.setStyleSheet(line_edit_style)
        self.input_sender.setStyleSheet(line_edit_style)
        self.input_recipient.setStyleSheet(line_edit_style)
        self.input_comment.setStyleSheet(line_edit_style)

        fields_layout.addRow("Наименование груза:", self.input_cargo_name)
        fields_layout.addRow("Отправитель:", self.input_sender)
        fields_layout.addRow("Получатель:", self.input_recipient)
        fields_layout.addRow("Примечание:", self.input_comment)

        extra_layout.addWidget(header_widget)
        extra_layout.addWidget(self.fields_container)

        main_layout.addWidget(extra_block)

        # Добавляем объединенный блок в основной layout
        layout.addWidget(main_block)

        # Состояние развернутости (по умолчанию свернуто)
        self.fields_expanded = False
        self.fields_container.setVisible(False)

        # Подключаем кнопку к слоту
        self.toggle_button.clicked.connect(self.toggle_extra_fields)

        layout.addStretch()

        # Таймер для чтения и эмуляции веса с обновлением информации
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.read_or_simulate_weight)
        self.timer.start(50)  # Уменьшаем интервал до 50мс для более быстрого чтения данных


        # Связываем кнопки с методами
        self.connect_button.clicked.connect(self.on_connect_clicked)
        self.disconnect_button.clicked.connect(self.on_disconnect_clicked)
        self.save_weight_button.clicked.connect(self.on_save_weight_clicked)
        self.auto_weight_checkbox.stateChanged.connect(self.on_auto_weighing_toggled)

        self.load_configurations_into_combo()
        self.update_info_display()
        self.update_auto_weighing_status()

        # Проверяем видимость блока веса при инициализации

        # Инициализируем менеджер отображения веса
        self.weight_display_manager = WeightDisplayManager(
            self.weight_label, self.status_label, font_family
        )

    def update_info_block_visibility(self):
        """Обновляет видимость блока информации о взвешивании"""
        if self.show_info_block:
            if not hasattr(self, 'info_block') or not self.info_block:
                # Создаем блок информации, если он отсутствует
                self._create_info_block()
        else:
            # Удаляем блок информации, если он существует
            if hasattr(self, 'info_block') and self.info_block:
                self.layout().removeWidget(self.info_block)
                self.info_block.deleteLater()
                self.info_block = None

    def _create_info_block(self):
        """Создает блок информации о взвешивании"""
        if hasattr(self, 'info_block') and self.info_block:
            return

        info_block = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(info_block)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(4)
        info_block.setStyleSheet("background: transparent;")

        label_info_title = QtWidgets.QLabel("ИНФОРМАЦИЯ О ВЗВЕШИВАНИИ")
        label_info_title.setStyleSheet("font-weight: bold; margin-bottom: 6px;")
        info_layout.addWidget(label_info_title)

        self.label_datetime = QtWidgets.QLabel("")
        info_layout.addWidget(self.label_datetime)

        self.label_operator = QtWidgets.QLabel("")
        info_layout.addWidget(self.label_operator)

        # Вставляем блок информации в начало layout
        layout = self.layout()
        layout.insertWidget(0, info_block)
        self.info_block = info_block

    def load_configurations_into_combo(self):
        self.config_combo.clear()
        if not self.current_user:
            return
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM com_configurations WHERE username=? ORDER BY id DESC', (self.current_user,))
        rows = cursor.fetchall()
        conn.close()
        names = [row[0] for row in rows]
        self.config_combo.addItems(names)

    def update_info_display(self):
        # Обновляем информацию только если блок информации включен
        if not self.show_info_block:
            return

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.label_datetime.setText(f"Дата и время: {now_str}")

        operator = self.current_user if self.current_user else "-"
        self.label_operator.setText(f"Оператор: {operator}")


        try:
            # Проверяем что weight_label существует и не удален
            if self.weight_label and hasattr(self.weight_label, 'text'):
                try:
                    weight_text = self.weight_label.text()
                    if weight_text and weight_text != "-":
                        weight = float(weight_text)
                    else:
                        weight = 0
                except (ValueError, RuntimeError):
                    weight = 0
            else:
                weight = 0
        except (ValueError, RuntimeError):
            weight = 0

        # Строка "Наличие груза" удалена по запросу пользователя

    def on_connect_clicked(self):
        current_config_name = self.config_combo.currentText()
        if not current_config_name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите конфигурацию для подключения.")
            return

        if not self.current_user:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Пользователь не авторизован.")
            return

        self.current_config_name = current_config_name
        self.update_info_display()

        # test mode removed
        self.timer.stop()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT port, baud, COALESCE(protocol, 1)
            FROM com_configurations
            WHERE username=? AND name=?
        ''', (self.current_user, current_config_name))
        row = cursor.fetchone()
        conn.close()

        if not row:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Конфигурация не найдена.")
            # Сбрасываем отображение веса при ошибке подключения
            if hasattr(self, 'weight_display_manager'):
                self.weight_display_manager.reset()
            self.update_connection_status(False)
            return

        port, baud, protocol = row
        baud = int(baud)
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = serial.Serial(port=port, baudrate=baud, timeout=1)
            self.timer.start(50)
            QtWidgets.QMessageBox.information(self, "Подключено",
                                               f"Подключение к {port} с скоростью {baud} успешно установлено.")
            self.update_connection_status(True, port, baud)
            # Сохраняем выбранный протокол для чтения
            self.current_protocol = int(protocol) if protocol else 1
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка подключения", str(e))
            self.serial_port = None
            self.update_connection_status(False)
            # Проверяем что weight_label существует перед установкой текста
            if self.weight_label and hasattr(self.weight_label, 'setText'):
                self.weight_label.setText("-")

    def on_disconnect_clicked(self):
        self.timer.stop()
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                QtWidgets.QMessageBox.information(self, "Отключено", "COM-порт успешно отключен.")
            else:
                QtWidgets.QMessageBox.information(self, "Информация", "COM-порт не был подключен.")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Ошибка", f"Ошибка при отключении: {e}")
        self.serial_port = None
        self.current_config_name = None
        
        # Сброс переменных автоматического взвешивания
        self._reset_auto_weighing_state()
        self.last_ui_update = 0.0
        self.last_auto_weigh_call = 0.0

        
        self.update_connection_status(False)
        # Сбрасываем отображение веса при отключении
        if hasattr(self, 'weight_display_manager'):
            self.weight_display_manager.reset()
        self.update_info_display()

    def read_or_simulate_weight(self):
        current_time = time.time() * 1000  # мс

        # Оптимизированное обновление интерфейса - только раз в секунду
        if current_time - self.last_ui_update > self.ui_update_interval:
            self.update_info_display()
            self.last_ui_update = current_time

        # Читаем данные из порта и сразу отображаем вес
        if self.serial_port and self.serial_port.in_waiting:
            try:
                # Читаем все доступные строки
                while self.serial_port.in_waiting:
                    raw_bytes = self.serial_port.readline()
                    if raw_bytes:
                        raw_string = raw_bytes.decode('utf-8').strip()
                        weight_value = self.parse_weight_from_raw(raw_string)
                        if weight_value is not None and isinstance(weight_value, (int, float)) and weight_value >= 0:
                            # Сразу отображаем вес без буферизации
                            self._update_weight_display(weight_value)

                            # Обрабатываем автоматическое взвешивание с ограничением частоты вызовов
                            current_time = time.time() * 1000  # мс
                            if current_time - self.last_auto_weigh_call > self.auto_weigh_interval:
                                self.process_auto_weighing(weight_value)
                                self.last_auto_weigh_call = current_time

            except Exception as e:
                print("Ошибка чтения с COM-порта:", e)


    def _update_weight_display(self, weight_value):
        """Обновляет отображение веса с использованием нового менеджера"""
        if hasattr(self, 'weight_display_manager'):
            self.weight_display_manager.update_weight(weight_value)


    def _process_auto_weighing_call(self, weight_value):
        """Обрабатывает вызов автоматического взвешивания с ограничением частоты"""
        try:
            current_time = time.time() * 1000  # мс
            if current_time - self.last_auto_weigh_call > self.auto_weigh_interval:
                self.process_auto_weighing(weight_value)
                self.last_auto_weigh_call = current_time
        except (AttributeError, RuntimeError):
            # Игнорируем ошибки если переменные недоступны
            pass

    def _handle_port_error(self, error):
        """Обрабатывает критические ошибки порта"""
        try:
            error_msg = f"Ошибка порта: {str(error)}"
            if hasattr(self, 'weight_display_manager'):
                # Сбрасываем отображение веса при ошибке порта
                self.weight_display_manager.reset()
        except (AttributeError, RuntimeError):
            pass

    def process_auto_weighing(self, current_weight):
        """Обрабатывает логику автоматического взвешивания"""
        # Проверяем, включено ли автоматическое взвешивание
        if not self.auto_weight_checkbox.isChecked():
            return

        # Проверяем, авторизован ли пользователь
        if not self.current_user:
            return

        current_time = time.time()

        # Если вес равен нулю, устанавливаем флаг сброса
        if current_weight == 0:
            self.weight_was_zero = True
            self.last_weight = None
            self.last_weight_time = None
            self.stable_weight_duration = 0
            return

        # Если вес не был сброшен на ноль после последнего сохранения, игнорируем
        if not self.weight_was_zero and self.last_saved_weight is not None:
            return

        # Получаем интервал стабилизации
        try:
            stabilization_interval = int(self.interval_input.text())
        except ValueError:
            stabilization_interval = 5  # По умолчанию 5 секунд

        # Если это новый вес или вес изменился
        if self.last_weight != current_weight:
            self.last_weight = current_weight
            self.last_weight_time = current_time
            self.stable_weight_duration = 0
        else:
            # Вес не изменился, увеличиваем время стабилизации
            if self.last_weight_time is not None:
                self.stable_weight_duration = current_time - self.last_weight_time

        # Если вес стабилен в течение заданного интервала и больше нуля
        if (self.stable_weight_duration >= stabilization_interval and
            current_weight > 0 and
            self.weight_was_zero):

            self.auto_save_weight(current_weight)

    def _reset_auto_weighing_state(self):
        """Сбрасывает состояние автоматического взвешивания"""
        self.weight_was_zero = True
        self.last_weight = None
        self.last_weight_time = None
        self.stable_weight_duration = 0

    def _get_stabilization_interval(self):
        """Получает интервал стабилизации с улучшенной обработкой ошибок"""
        try:
            interval = int(self.interval_input.text() or "3")
            # Ограничиваем диапазон 1-30 секунд
            return max(1, min(30, interval))
        except (ValueError, AttributeError):
            return 3  # Значение по умолчанию

    def _update_weight_stability(self, current_weight, current_time):
        """Обновляет состояние стабильности веса и возвращает True если вес изменился"""
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

    def auto_save_weight(self, weight):
        """Автоматически сохраняет вес"""
        try:
            # Получаем текущую дату и время
            current_datetime = datetime.now().strftime("%d.%m.%Y %H:%M")

            # Получаем данные из полей ввода
            cargo_name = self.input_cargo_name.text().strip() or '-'
            sender = self.input_sender.text().strip() or '-'
            recipient = self.input_recipient.text().strip() or '-'
            comment = self.input_comment.toPlainText().strip() or '-'

            # Получаем название весов
            scales_name = self.current_config_name or '-'

            # Сохраняем в базу данных
            save_weighing(
                datetime_str=current_datetime,
                weight=weight,
                operator=self.current_user,
                weighing_mode='Автоматическое',
                cargo_name=cargo_name,
                sender=sender,
                recipient=recipient,
                comment=comment,
                scales_name=scales_name
            )


            # Устанавливаем флаги для предотвращения повторного сохранения
            self.last_saved_weight = weight
            self.weight_was_zero = False

            # Уведомляем левую панель о новом взвешивании
            self.weighing_saved.emit()

            print(f"Автоматически сохранен вес: {weight} кг")

        except Exception as e:
            print(f"Ошибка при автоматическом сохранении: {str(e)}")

    def _validate_auto_save_data(self, weight):
        """Проверяет валидность данных для автоматического сохранения"""
        if not isinstance(weight, (int, float)) or weight <= 0:
            return False

        if not self.current_user:
            return False

        if not self.serial_port or not self.serial_port.is_open:
            return False

        return True

    def _get_form_data(self):
        """Получает данные из полей ввода с проверкой существования объектов"""
        try:
            return {
                'cargo_name': self.input_cargo_name.text().strip() or '-',
                'sender': self.input_sender.text().strip() or '-',
                'recipient': self.input_recipient.text().strip() or '-',
                'comment': self.input_comment.toPlainText().strip() or '-'
            }
        except (AttributeError, RuntimeError):
            # Объекты полей ввода были удалены или недоступны
            return None

    def _update_auto_save_status(self, success, weight, error_msg=None):
        """Обновляет статус автоматического сохранения для отображения пользователю"""
        try:
            if success:
                status_text = f"Автоматически сохранен вес: {weight:.1f} кг"
            else:
                status_text = f"Ошибка автосохранения: {error_msg or 'Неизвестная ошибка'}"

            # Можно добавить временное отображение статуса в интерфейсе
            # Например, изменить цвет метки или показать всплывающее сообщение

        except (AttributeError, RuntimeError):
            # Игнорируем ошибки обновления статуса если объекты недоступны
            pass

    def on_auto_weighing_toggled(self):
        """Обработчик изменения состояния чекбокса автоматического взвешивания"""
        self.update_auto_weighing_status()


    def update_auto_weighing_status(self):
        """Обновляет отображение статуса автоматического взвешивания в блоке с весом"""
        if self.auto_weight_checkbox.isChecked():
            self.auto_weight_label.setText("Автоматическое взвешивание\nвключено")
        else:
            self.auto_weight_label.setText("Автоматическое взвешивание\nвыключено")


    def update_connection_status(self, is_connected, port=None, baud=None):
        """Обновляет статус подключения с использованием нового менеджера"""
        if hasattr(self, 'weight_display_manager'):
            self.weight_display_manager.update_connection_status(is_connected, port, baud)

    def on_save_weight_clicked(self):
        """Обработчик нажатия кнопки 'Сохранить вес'"""
        # Проверяем, авторизован ли пользователь
        if not self.current_user:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Для сохранения веса необходимо авторизоваться.")
            return
        
        # Получаем текущий вес
        try:
            # Проверяем что weight_label существует и не удален
            if self.weight_label and hasattr(self.weight_label, 'text'):
                try:
                    weight_text = self.weight_label.text()
                    if weight_text and weight_text != "-":
                        weight = float(weight_text)
                    else:
                        weight = 0
                except (ValueError, RuntimeError):
                    weight = 0
            else:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удается получить значение веса.")
                return

            if weight <= 0:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Некорректный вес для сохранения.")
                return
        except (ValueError, RuntimeError):
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удается получить значение веса.")
            return
        
        # Получаем текущую дату и время
        current_datetime = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Получаем данные из полей ввода
        cargo_name = self.input_cargo_name.text().strip() or '-'
        sender = self.input_sender.text().strip() or '-'
        recipient = self.input_recipient.text().strip() or '-'
        comment = self.input_comment.toPlainText().strip() or '-'
        
        # Получаем название весов
        scales_name = self.current_config_name or '-'
        
        try:
            # Сохраняем в базу данных
            save_weighing(
                datetime_str=current_datetime,
                weight=weight,
                operator=self.current_user,
                weighing_mode='Ручное',
                cargo_name=cargo_name,
                sender=sender,
                recipient=recipient,
                comment=comment,
                scales_name=scales_name
            )
            
            
            # Устанавливаем флаги для автоматического взвешивания
            self.last_saved_weight = weight
            self.weight_was_zero = False
            
            # Уведомляем левую панель о новом взвешивании
            self.weighing_saved.emit()
            
            QtWidgets.QMessageBox.information(self, "Успех", f"Вес {weight} кг успешно сохранен.")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")



    def toggle_extra_fields(self):
        """Переключает видимость полей дополнительной информации"""
        self.fields_expanded = not self.fields_expanded
        self.fields_container.setVisible(self.fields_expanded)

        # Меняем текст кнопки
        if self.fields_expanded:
            self.toggle_button.setText("▲")
            self.toggle_button.setToolTip("Свернуть поля ввода")
        else:
            self.toggle_button.setText("▼")
            self.toggle_button.setToolTip("Развернуть поля ввода")
    
    

    def parse_weight_from_raw(self, raw_string: str):
        """Парсит строку веса в зависимости от текущего протокола.
        Протокол 1: строки вида 'ww00020.12kg' -> число 20.12
        Протокол 2: строки вида 'ST, GS,+000005 kg' -> число 5
        """
        if not raw_string or not raw_string.strip():
            return None

        protocol = getattr(self, 'current_protocol', 1)

        try:
            if protocol == 2:
                # Протокол 2: строки вида 'ST, GS,+000005 kg'
                # Ищем образец с числом и 'kg' в конце, может содержать + и пробелы
                match = re.search(r'[A-Z]{2},\s*GS,\s*[+\-]?\s*(\d+(?:\.\d+)?)\s*kg', raw_string.strip())
                if match:
                    value_str = match.group(1).strip()
                    try:
                        value = float(value_str) if '.' in value_str else int(value_str)
                        return value if value >= 0 else None
                    except ValueError:
                        pass
            else:
                # Протокол 1: строки вида 'ww00020.12kg' или 'ww 00020.12 kg'
                # Ищем ww + любое количество цифр + необязательная десятичная часть + kg
                match = re.search(r'ww\s*(\d+(?:\.\d+)?)\s*kg', raw_string.strip().lower())
                if match:
                    value_str = match.group(1).strip()
                    try:
                        value = float(value_str) if '.' in value_str else int(value_str)
                        return value if value >= 0 else None
                    except ValueError:
                        pass

                # Альтернативный формат без 'kg' но с 'ww'
                alt_match = re.search(r'ww\s*(\d+(?:\.\d+)?)', raw_string.strip().lower())
                if alt_match:
                    value_str = alt_match.group(1).strip()
                    try:
                        value = float(value_str) if '.' in value_str else int(value_str)
                        return value if value >= 0 else None
                    except ValueError:
                        pass

            # Если основные протоколы не сработали, ищем числа с десятичной точкой или запятой
            # Но только если они выглядят как вес (положительные числа)
            number_patterns = [
                r'(\d+(?:[.,]\d+)?)',  # числа с точкой или запятой как разделителем
            ]

            for pattern in number_patterns:
                matches = re.findall(pattern, raw_string.strip())
                for match in matches:
                    # Заменяем запятую на точку для корректного преобразования
                    value_str = match.replace(',', '.')
                    try:
                        value = float(value_str)
                        # Проверяем, что это разумное значение веса (не слишком большое)
                        if 0 <= value <= 100000:  # Разумный предел для веса в кг
                            return value
                    except ValueError:
                        continue

        except Exception:
            # Игнорируем любые ошибки парсинга
            pass

        return None
