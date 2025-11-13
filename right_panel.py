import sqlite3
import time
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui
from weight_display_controller import WeightDisplayController
from weight_reader import WeightReader
from auto_weighing_engine import AutoWeighingEngine
from weighing_service import WeighingService

DB_FILE = 'weights_journal.db'

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
        self.scales_number = scales_number  # Сохраняем номер весов
        self.setFixedWidth(437)
        self.setStyleSheet("background-color: #f9fafb; font-size: 10pt;")
        self.show_info_block = show_info_block
        self.printer_manager = None  # Менеджер термопринтера

        # Инициализируем компоненты
        self.weight_reader = WeightReader()
        self.auto_weighing_engine = AutoWeighingEngine(user=self.current_user, scales_name=self.current_config_name)
        self.weighing_service = WeighingService()

        # Оптимизация обновления интерфейса
        self.last_ui_update = 0.0
        self.ui_update_interval = 100  # Обновляем интерфейс раз в 100мс для баланса производительности

        # Оптимизация автоматического взвешивания
        self.last_auto_weigh_call = 0.0
        self.auto_weigh_interval = 100  # Интервал вызовов автоматического взвешивания (мс) для более быстрой реакции

        # Механизм повторных попыток подключения
        self.connection_retry_count = 0
        self.max_connection_retries = 3
        self.connection_retry_delay = 2000  # мс, задержка между попытками
        self.last_connection_attempt = 0.0
        self.connection_lost = False

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
            delete_button = QtWidgets.QPushButton()
            delete_icon = QtGui.QIcon("static/delete.svg")
            delete_button.setIcon(delete_icon)
            delete_button.setIconSize(QtCore.QSize(30, 30))
            delete_button.setFixedSize(30, 30)
            # Центрируем текст в кнопке
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 3px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #fecaca;
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
        icon = QtGui.QIcon("static/save_ves.svg")
        self.save_weight_button.setIcon(icon)
        self.save_weight_button.setIconSize(QtCore.QSize(32, 32))
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

        self.receipt_checkbox = QtWidgets.QCheckBox("Чекопечать")
        checkbox_layout.addWidget(self.receipt_checkbox)

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
        self.timer.start(100)  # Уменьшаем интервал до 50мс для более быстрого чтения данных


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
        self.weight_display_manager = WeightDisplayController(
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

        # Используем WeightReader для подключения
        success, message = self.weight_reader.connect(port, baud)
        if success:
            self.timer.start(50)
            QtWidgets.QMessageBox.information(self, "Подключено",
                                               f"Подключение к {port} с скоростью {baud} успешно установлено.")
            self.update_connection_status(True, port, baud)
            # Сохраняем выбранный протокол для чтения
            self.weight_reader.set_protocol(int(protocol) if protocol else 1)
            self.current_protocol = int(protocol) if protocol else 1
        else:
            QtWidgets.QMessageBox.critical(self, "Ошибка подключения", message)
            self.update_connection_status(False)
            # Проверяем что weight_label существует перед установкой текста
            if self.weight_label and hasattr(self.weight_label, 'setText'):
                self.weight_label.setText("-")

    def on_disconnect_clicked(self):
        self.timer.stop()
        self.weight_reader.disconnect()
        QtWidgets.QMessageBox.information(self, "Отключено", "COM-порт успешно отключен.")
        self.current_config_name = None

        # Сброс состояний
        self.auto_weighing_engine.reset_state()
        self.last_ui_update = 0.0
        self.last_auto_weigh_call = 0.0

        # Сброс счетчиков попыток переподключения
        self.connection_retry_count = 0
        self.connection_lost = False

        self.update_connection_status(False)
        # Сбрасываем отображение веса при отключении
        if hasattr(self, 'weight_display_manager'):
            self.weight_display_manager.reset()
        self.update_info_display()

    def read_or_simulate_weight(self):
        try:
            current_time = time.time() * 1000  # мс

            # Оптимизированное обновление интерфейса - только раз в секунду
            if current_time - self.last_ui_update > self.ui_update_interval:
                self.update_info_display()
                self.last_ui_update = current_time

            # Читаем данные из порта и сразу отображаем вес
            weight_value = self.weight_reader.read_weight()
            if weight_value is not None:
                # Сбрасываем счетчик попыток при успешном чтении
                self.connection_retry_count = 0
                self.connection_lost = False

                # Сразу отображаем вес без буферизации
                self._update_weight_display(weight_value)

                # Обрабатываем автоматическое взвешивание с ограничением частоты вызовов
                current_time = time.time() * 1000  # мс
                if current_time - self.last_auto_weigh_call > self.auto_weigh_interval:
                    self.process_auto_weighing(weight_value)
                    self.last_auto_weigh_call = current_time
            else:
                # Если не удалось прочитать вес, проверяем на разрыв соединения
                self._handle_connection_loss()

        except Exception as e:
            # Логируем ошибку и обрабатываем разрыв соединения
            print(f"Ошибка в read_or_simulate_weight: {str(e)}")
            self._handle_connection_loss()


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

    def _handle_connection_loss(self):
        """Обрабатывает потерю соединения и пытается восстановить подключение"""
        if not self.connection_lost:
            self.connection_lost = True
            print("Соединение с весами потеряно, начинаем попытки переподключения...")
            self.update_connection_status(False)

        # Проверяем, можно ли начать новую попытку переподключения
        current_time = time.time() * 1000
        if current_time - self.last_connection_attempt > self.connection_retry_delay:
            if self.connection_retry_count < self.max_connection_retries:
                self.connection_retry_count += 1
                self.last_connection_attempt = current_time
                print(f"Попытка переподключения #{self.connection_retry_count}")

                # Пытаемся переподключиться
                try:
                    if self.current_config_name and self.current_user:
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT port, baud, COALESCE(protocol, 1)
                            FROM com_configurations
                            WHERE username=? AND name=?
                        ''', (self.current_user, self.current_config_name))
                        row = cursor.fetchone()
                        conn.close()

                        if row:
                            port, baud, protocol = row
                            success, message = self.weight_reader.connect(port, int(baud))
                            if success:
                                print("Переподключение успешно!")
                                self.timer.start(50)
                                self.update_connection_status(True, port, int(baud))
                                self.weight_reader.set_protocol(int(protocol) if protocol else 1)
                                self.current_protocol = int(protocol) if protocol else 1
                                # Сбрасываем счетчики при успешном переподключении
                                self.connection_retry_count = 0
                                self.connection_lost = False
                                return
                            else:
                                print(f"Попытка переподключения #{self.connection_retry_count} не удалась: {message}")
                        else:
                            print("Не удалось получить конфигурацию для переподключения")
                    else:
                        print("Отсутствует конфигурация или пользователь для переподключения")
                except Exception as e:
                    print(f"Ошибка при попытке переподключения: {str(e)}")

                # Если все попытки исчерпаны
                if self.connection_retry_count >= self.max_connection_retries:
                    print("Все попытки переподключения исчерпаны")
                    self.timer.stop()  # Останавливаем таймер для предотвращения дальнейших зависаний
                    # Можно добавить уведомление пользователю здесь
            else:
                # Все попытки исчерпаны, останавливаемся
                pass

    def process_auto_weighing(self, current_weight):
        """Обрабатывает логику автоматического взвешивания"""
        # Проверяем, включено ли автоматическое взвешивание
        if not self.auto_weight_checkbox.isChecked():
            return

        # Обновляем настройки стабилизации
        try:
            stabilization_interval = int(self.interval_input.text())
            self.auto_weighing_engine.set_stabilization_interval(stabilization_interval)
        except ValueError:
            pass  # Используем значение по умолчанию

        # Обрабатываем вес через движок автоматического взвешивания
        should_save, status_message = self.auto_weighing_engine.process_weight(current_weight)

        if should_save:
            # Автоматическая чекопечать если включена
            if self.receipt_checkbox.isChecked():
                self._perform_auto_print_receipt(current_weight)

            print(f"Автоматически сохранен вес: {current_weight} кг")

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

    def _perform_auto_print_receipt(self, weight):
        """Выполняет автоматическую печать чека"""
        try:
            # Получаем данные для чека
            current_datetime = datetime.now().strftime("%d.%m.%Y %H:%M")
            cargo_name = self.input_cargo_name.text().strip() or '-'
            sender = self.input_sender.text().strip() or '-'
            recipient = self.input_recipient.text().strip() or '-'
            comment = self.input_comment.toPlainText().strip() or '-'
            scales_name = self.current_config_name or '-'

            receipt_data = {
                "datetime": current_datetime,
                "weight": str(weight),
                "operator": self.current_user,
                "mode": "Автоматическое",
                "name": cargo_name,
                "warehouse": scales_name,
                "sender": sender,
                "receiver": recipient,
                "notes": comment
            }

            # Используем переданный printer_manager
            if hasattr(self, 'printer_manager') and self.printer_manager:
                success, message = self.printer_manager.print_receipt(receipt_data)
                if success:
                    print(f"Чек автоматически распечатан: {weight} кг")
                else:
                    print(f"Ошибка при автоматической чекопечати: {message}")
            else:
                print("Ошибка: менеджер термопринтера не доступен")

        except Exception as e:
            print(f"Ошибка при автоматической печати чека: {str(e)}")

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

        # Получаем данные из полей ввода
        cargo_name = self.input_cargo_name.text().strip() or '-'
        sender = self.input_sender.text().strip() or '-'
        recipient = self.input_recipient.text().strip() or '-'
        comment = self.input_comment.toPlainText().strip() or '-'

        # Получаем название весов
        scales_name = self.current_config_name or '-'

        # Используем WeighingService для сохранения
        success = self.weighing_service.save_manual_weighing(
            weight=weight,
            operator=self.current_user,
            cargo_name=cargo_name,
            sender=sender,
            recipient=recipient,
            comment=comment,
            scales_name=scales_name
        )

        if success:
            # Устанавливаем флаги для автоматического взвешивания
            self.auto_weighing_engine.reset_state()

            # Уведомляем левую панель о новом взвешивании
            self.weighing_saved.emit()

            QtWidgets.QMessageBox.information(self, "Успех", f"Вес {weight} кг успешно сохранен.")
        else:
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Ошибка при сохранении веса.")



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
    
    

    # Метод parse_weight_from_raw больше не нужен, так как логика переехала в WeightReader
