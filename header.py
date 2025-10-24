from PyQt5 import QtWidgets, QtCore, QtGui


class HeaderWidget(QtWidgets.QWidget):
    system_clicked = QtCore.pyqtSignal()
    login_clicked = QtCore.pyqtSignal()
    logout_clicked = QtCore.pyqtSignal()
    add_scales_clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.logged_in_user = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_bar = QtWidgets.QWidget()
        top_bar.setStyleSheet("""
            background-color: #f3f4f6;
            border-bottom: 1px solid #d1d5db;
            padding: 4px 16px;
        """)
        top_layout = QtWidgets.QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Левый блок - логотип и кнопки объединены
        left_widget = QtWidgets.QWidget()
        # Стилизация для flat-кнопок с эффектом изменения фона при наведении
        left_widget.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                text-decoration: none;
                font-size: 12pt;  /* Увеличенный размер шрифта */
                font-family: Arial, Helvetica, sans-serif;  /* Шрифт Arial, Helvetica */
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        left_layout = QtWidgets.QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Логотип первый
        self.logo_label = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap("static/logo_nv.png")
        # Масштабируем логотип до нужного размера
        scaled_pixmap = pixmap.scaled(150, 40, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.logo_label.setPixmap(scaled_pixmap)
        left_layout.addWidget(self.logo_label)

        # Кнопки в нужном порядке: Файл -> Настройки подключения -> Справка
        self.btn_file = QtWidgets.QPushButton("Файл")
        self.btn_file.setFlat(True)  # Убираем стандартный вид кнопки

        # Создаем выпадающее меню для кнопки Файл
        self.file_menu = QtWidgets.QMenu(self.btn_file)
        self.file_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 0;
            }
            QMenu::item {
                background-color: transparent;
                padding: 8px 16px;
                color: black;
                font-size: 11pt;
            }
            QMenu::item:selected {
                background-color: #f3f4f6;
                color: black;
            }
            QMenu::item:hover {
                background-color: #f3f4f6;
                color: black;
            }
        """)
        self.exit_action = QtWidgets.QAction("Закрыть программу", self)
        self.exit_action.triggered.connect(self.close_application)
        self.file_menu.addAction(self.exit_action)

        self.add_scales_action = QtWidgets.QAction("Добавить весы", self)
        self.add_scales_action.triggered.connect(self.add_scales_clicked.emit)
        self.file_menu.addAction(self.add_scales_action)

        # Подключаем меню к кнопке
        self.btn_file.setMenu(self.file_menu)

        self.btn_system = QtWidgets.QPushButton("Настройки подключения к весам")
        self.btn_system.setFlat(True)  # Убираем стандартный вид кнопки
        self.btn_system.clicked.connect(self.system_clicked.emit)

        self.btn_help = QtWidgets.QPushButton("Справка")
        self.btn_help.setFlat(True)  # Убираем стандартный вид кнопки

        # Подключаем обработчик для кнопки Справка
        self.btn_help.clicked.connect(self.show_about_program)

        left_layout.addWidget(self.btn_file)
        left_layout.addWidget(self.btn_system)
        left_layout.addWidget(self.btn_help)

        top_layout.addWidget(left_widget, alignment=QtCore.Qt.AlignLeft)

        # Правая часть - пользовательские элементы
        right_widget = QtWidgets.QWidget()
        right_widget.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        right_layout = QtWidgets.QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Добавляем надпись "Пользователь:" слева от кнопки пользователя
        self.user_label = QtWidgets.QLabel("Пользователь:")
        self.user_label.setStyleSheet("font-size: 11pt; margin-right: 0px;")
        self.user_label.setVisible(False)  # по умолчанию скрыта
        right_layout.addWidget(self.user_label)

        self.user_button = QtWidgets.QPushButton("Войти")
        user_icon = QtGui.QIcon("static/user_icon.svg")
        # Увеличиваем размер иконки пользователя еще больше
        self.user_button.setIconSize(QtCore.QSize(40, 40))  # Максимальный размер иконки
        self.user_button.setIcon(user_icon)
        self.user_button.setStyleSheet("font-size: 11pt; margin-left: 0px;")
        self.user_button.clicked.connect(self.login_clicked.emit)
        right_layout.addWidget(self.user_button)

        self.logout_button = QtWidgets.QPushButton("Завершить сеанс")
        self.logout_button.setStyleSheet("font-size: 11pt;")
        self.logout_button.clicked.connect(self.logout_clicked.emit)
        self.logout_button.setVisible(False)
        right_layout.addWidget(self.logout_button)

        top_layout.addWidget(right_widget, alignment=QtCore.Qt.AlignRight)

        header_label = QtWidgets.QLabel("ЖУРНАЛ ВЗВЕШИВАНИЙ")
        header_label.setStyleSheet("""
            background-color: #3a5c7e;
            color: white;
            padding: 8px 16px;
            font-size: 12pt;
            font-weight: 600;
        """)
        header_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        layout.addWidget(top_bar)
        # Заголовок "ЖУРНАЛ ВЗВЕШИВАНИЙ" перенесен в левую панель
        # layout.addWidget(header_label)

    def close_application(self):
        """Закрывает приложение"""
        QtWidgets.QApplication.quit()

    def show_about_program(self):
        """Показывает информацию о программе"""
        about_text = """
        <div style='text-align: center;'>
            <h3>О программе</h3>
            <p><b>Пользователь:</b> Пользователь Windows</p>
            <p><b>Ключ защиты:</b> Информация отсутствует</p>
            <p><b>Разработчик:</b> Zuev A.D</p>
            <p><b>Версия:</b> 0.8.2</p>
        </div>
        """

        QtWidgets.QMessageBox.about(
            self,
            "О программе - Журнал взвешиваний",
            about_text
        )

    def set_logged_in_user(self, username):
        self.logged_in_user = username
        self.user_label.setVisible(True)      # Показываем "Пользователь:"
        self.user_button.setText(username)
        self.user_button.setIcon(QtGui.QIcon())
        self.user_button.setEnabled(False)
        try:
            self.user_button.clicked.disconnect()
        except TypeError:
            pass
        self.logout_button.setVisible(True)

    def logout(self):
        self.logged_in_user = None
        self.user_label.setVisible(False)     # Скрываем "Пользователь:"
        self.user_button.setText("Войти")
        user_icon = QtGui.QIcon("static/user_icon.svg")
        self.user_button.setIcon(user_icon)
        self.user_button.setEnabled(True)
        try:
            self.user_button.clicked.disconnect()
        except TypeError:
            pass
        self.user_button.clicked.connect(self.login_clicked.emit)
        self.logout_button.setVisible(False)
