from PyQt5 import QtWidgets, QtCore
import serial.tools.list_ports


class ThermalPrinterDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, printer_manager=None):
        super().__init__(parent)
        self.printer_manager = printer_manager
        self.setWindowTitle("Настройки термопринтера")
        self.setModal(True)
        self.resize(400, 200)

        self.init_ui()
        self.load_settings()
        self.update_connection_status()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Группа настроек подключения
        connection_group = QtWidgets.QGroupBox("Настройки подключения")
        connection_layout = QtWidgets.QFormLayout(connection_group)

        # COM порт
        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.addItems(self.printer_manager.get_available_ports())
        connection_layout.addRow("COM порт:", self.port_combo)

        refresh_ports_btn = QtWidgets.QPushButton("Обновить порты")
        refresh_ports_btn.clicked.connect(self.refresh_ports)
        connection_layout.addRow("", refresh_ports_btn)

        # Скорость передачи
        self.baud_combo = QtWidgets.QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baud_combo.setCurrentText('9600')
        connection_layout.addRow("Скорость:", self.baud_combo)

        layout.addWidget(connection_group)

        # Статус подключения
        status_group = QtWidgets.QGroupBox("Статус")
        status_layout = QtWidgets.QVBoxLayout(status_group)

        self.status_label = QtWidgets.QLabel("Не подключен")
        status_layout.addWidget(self.status_label)

        layout.addWidget(status_group)

        # Кнопки
        buttons_layout = QtWidgets.QHBoxLayout()

        self.connect_btn = QtWidgets.QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self.connect_printer)
        buttons_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QtWidgets.QPushButton("Отключиться")
        self.disconnect_btn.clicked.connect(self.disconnect_printer)
        self.disconnect_btn.setEnabled(False)
        buttons_layout.addWidget(self.disconnect_btn)

        close_btn = QtWidgets.QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def refresh_ports(self):
        """Обновить список COM портов"""
        self.port_combo.clear()
        ports = self.printer_manager.get_available_ports()
        self.port_combo.addItems(ports)
        if ports:
            self.port_combo.setCurrentIndex(0)

    def connect_printer(self):
        """Подключиться к принтеру"""
        port = self.port_combo.currentText()
        baud_rate = int(self.baud_combo.currentText())

        if not port:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите COM порт!")
            return

        success, message = self.printer_manager.connect(port, baud_rate)
        if success:
            QtWidgets.QMessageBox.information(self, "Успех", message)
        else:
            QtWidgets.QMessageBox.critical(self, "Ошибка", message)

        self.update_connection_status()

    def disconnect_printer(self):
        """Отключиться от принтера"""
        self.printer_manager.disconnect()
        QtWidgets.QMessageBox.information(self, "Успех", "Отключено от принтера")
        self.update_connection_status()

    def update_connection_status(self):
        """Обновить статус подключения"""
        if self.printer_manager.is_connected:
            self.status_label.setText(f"Подключен к {self.printer_manager.port}")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
        else:
            self.status_label.setText("Не подключен")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)

    def load_settings(self):
        """Загрузить сохраненные настройки"""
        # Здесь можно добавить загрузку настроек из файла или базы данных
        # Пока оставим пустым
        pass

    def save_settings(self):
        """Сохранить настройки"""
        # Здесь можно добавить сохранение настроек
        # Пока оставим пустым
        pass