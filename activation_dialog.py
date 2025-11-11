from PyQt5 import QtWidgets, QtCore
import license_manager

class ActivationDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Активация лицензии")
        self.setModal(True)
        self.resize(400, 250)

        layout = QtWidgets.QVBoxLayout()

        # Инструкции
        instructions = QtWidgets.QLabel("Для активации лицензии введите код активации:")
        layout.addWidget(instructions)

        # Показываем UUID системы
        system_uuid = license_manager.get_system_uuid()
        uuid_label = QtWidgets.QLabel(f"UUID системы: {system_uuid}")
        uuid_label.setStyleSheet("font-family: monospace; background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        layout.addWidget(uuid_label)

        # Поле для ввода кода
        self.code_input = QtWidgets.QLineEdit()
        self.code_input.setPlaceholderText("Код активации")
        layout.addWidget(self.code_input)

        # Кнопки
        buttons_layout = QtWidgets.QHBoxLayout()

        activate_button = QtWidgets.QPushButton("Активировать")
        activate_button.clicked.connect(self.activate_license)
        buttons_layout.addWidget(activate_button)

        cancel_button = QtWidgets.QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def activate_license(self):
        code = self.code_input.text().strip()
        if license_manager.activate_license(code):
            QtWidgets.QMessageBox.information(self, "Успех", "Лицензия успешно активирована!")
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Неверный код активации.")