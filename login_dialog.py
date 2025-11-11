import sqlite3
from PyQt5 import QtWidgets, QtGui, QtCore

DB_FILE = 'weights_journal.db'

def init_user_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авторизация оператора")
        self.setFixedSize(320, 220)

        layout = QtWidgets.QVBoxLayout(self)

        # Добавляем иконку вверху
        icon_layout = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel()
        icon = QtGui.QIcon("static/210222.svg")
        icon_pixmap = icon.pixmap(100, 100)  # Растянутая в ширину иконка
        icon_label.setPixmap(icon_pixmap)
        icon_label.setScaledContents(True)  # Разрешаем масштабирование содержимого
        icon_layout.addWidget(icon_label, alignment=QtCore.Qt.AlignCenter)
        layout.addLayout(icon_layout)

        form_layout = QtWidgets.QFormLayout()
        self.username_combo = QtWidgets.QComboBox()
        self.username_combo.setEditable(True)  # Разрешаем ввод нового пользователя
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        form_layout.addRow("Имя пользователя:", self.username_combo)
        form_layout.addRow("Пароль:", self.password_edit)
        layout.addLayout(form_layout)

        button_layout = QtWidgets.QHBoxLayout()
        self.login_button = QtWidgets.QPushButton("Вход")
        self.add_user_button = QtWidgets.QPushButton("Добавить нового пользователя")
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.add_user_button)
        layout.addLayout(button_layout)

        self.login_button.clicked.connect(self.login)
        self.add_user_button.clicked.connect(self.add_user)

        self.logged_in_user = None

        # Загружаем список пользователей при инициализации
        self.load_users()

    def load_users(self):
        """Загружает список пользователей в комбо-бокс"""
        self.username_combo.clear()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER BY username")
        users = cursor.fetchall()
        conn.close()

        # Добавляем пользователей в комбо-бокс
        for user in users:
            self.username_combo.addItem(user[0])

    def login(self):
        username = self.username_combo.currentText().strip()
        password = self.password_edit.text().strip()

        if not username or not password:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя пользователя и пароль")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Пользователь не найден")
            return

        if row[0] != password:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Неверный пароль")
            return

        self.logged_in_user = username
        QtWidgets.QMessageBox.information(self, "Успех", f"Добро пожаловать, {username}!")
        self.accept()

    def add_user(self):
        username = self.username_combo.currentText().strip()
        password = self.password_edit.text().strip()

        if not username or not password:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя пользователя и пароль для добавления")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Пользователь с таким именем уже существует")
            conn.close()
            return
        conn.close()

        QtWidgets.QMessageBox.information(self, "Успех", f"Пользователь {username} добавлен")
        # Обновляем список пользователей после добавления нового
        self.load_users()
        # Очищаем поля
        self.username_combo.setCurrentText("")
        self.password_edit.clear()

init_user_table()
