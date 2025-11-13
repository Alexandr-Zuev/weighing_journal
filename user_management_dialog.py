import sqlite3
from PyQt5 import QtWidgets, QtCore

DB_FILE = 'weights_journal.db'

class UserManagementDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление пользователями")
        self.resize(500, 400)

        layout = QtWidgets.QVBoxLayout(self)

        # Таблица пользователей
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Имя пользователя", "Пароль"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        # Кнопки
        buttons_layout = QtWidgets.QHBoxLayout()
        self.delete_button = QtWidgets.QPushButton("Удалить выбранного пользователя")
        self.delete_button.clicked.connect(self.delete_user)
        buttons_layout.addWidget(self.delete_button)

        self.change_password_button = QtWidgets.QPushButton("Изменить пароль")
        self.change_password_button.clicked.connect(self.change_password)
        buttons_layout.addWidget(self.change_password_button)

        buttons_layout.addStretch()

        self.close_button = QtWidgets.QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)

        layout.addLayout(buttons_layout)

        self.load_users()

        # Стилизация таблицы
        self.table.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 10pt;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                font-family: Arial;
                font-size: 11pt;
            }
            QTableWidget::item {
                padding: 4px;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)

    def load_users(self):
        """Загружает список пользователей в таблицу"""
        self.table.setRowCount(0)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT username, password FROM users ORDER BY username")
        users = cursor.fetchall()
        conn.close()

        for row_data in users:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate(row_data):
                self.table.setItem(row, col, QtWidgets.QTableWidgetItem(str(val)))

        # Автоматическая подстройка ширины столбцов
        for col in range(self.table.columnCount()):
            self.table.resizeColumnToContents(col)

    def change_password(self):
        """Изменяет пароль выбранного пользователя"""
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите пользователя для изменения пароля")
            return

        # Получаем имя пользователя
        row = selected[0].row()
        username = self.table.item(row, 0).text()

        # Диалог для ввода нового пароля
        new_password, ok = QtWidgets.QInputDialog.getText(
            self, "Изменение пароля", f"Введите новый пароль для пользователя '{username}':",
            QtWidgets.QLineEdit.Password
        )

        if ok and new_password.strip():
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password=? WHERE username=?", (new_password.strip(), username))
            conn.commit()
            conn.close()

            QtWidgets.QMessageBox.information(self, "Успех", f"Пароль пользователя '{username}' изменен")
            self.load_users()  # Обновляем таблицу
        elif ok and not new_password.strip():
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Пароль не может быть пустым")

    def delete_user(self):
        """Удаляет выбранного пользователя"""
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите пользователя для удаления")
            return

        # Получаем имя пользователя
        row = selected[0].row()
        username = self.table.item(row, 0).text()

        # Не даем удалить админа
        if username == "admin":
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Невозможно удалить администратора")
            return

        # Подтверждение удаления
        reply = QtWidgets.QMessageBox.question(
            self,
            'Подтверждение удаления',
            f'Вы действительно хотите удалить пользователя "{username}"?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username=?", (username,))
            conn.commit()
            conn.close()

            QtWidgets.QMessageBox.information(self, "Успех", f"Пользователь '{username}' удален")
            self.load_users()  # Обновляем таблицу