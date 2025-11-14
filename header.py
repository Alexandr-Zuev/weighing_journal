from PyQt5 import QtWidgets, QtCore, QtGui
import license_manager


class HeaderWidget(QtWidgets.QWidget):
    system_clicked = QtCore.pyqtSignal()
    printer_config_clicked = QtCore.pyqtSignal()
    login_clicked = QtCore.pyqtSignal()
    logout_clicked = QtCore.pyqtSignal()
    add_scales_clicked = QtCore.pyqtSignal()
    user_management_clicked = QtCore.pyqtSignal()
    delete_record_clicked = QtCore.pyqtSignal()

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
        # Загружаем шрифт NotoSans-Regular.ttf
        font_id = QtGui.QFontDatabase.addApplicationFont("static/NotoSans-Regular.ttf")
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        header_font_family = font_families[0] if font_families else "Arial, Helvetica, sans-serif"

        # Стилизация для flat-кнопок с эффектом изменения фона при наведении
        left_widget.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                text-decoration: none;
                font-size: 12pt;  /* Увеличенный размер шрифта */
                font-family: {header_font_family};  /* Шрифт NotoSans-Regular */
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #e5e7eb;
            }}
        """)
        left_layout = QtWidgets.QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Убираем статус лицензии из хедера

        # Логотип первый
        self.logo_label = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap("static/logo_nv.png")
        # Масштабируем логотип до нужного размера
        scaled_pixmap = pixmap.scaled(150, 40, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.logo_label.setPixmap(scaled_pixmap)
        left_layout.addWidget(self.logo_label)

        # Кнопки в нужном порядке: Файл -> Настройки -> Справка
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
        self.add_scales_action = QtWidgets.QAction("Добавить весы", self)
        self.add_scales_action.triggered.connect(self.add_scales_clicked.emit)
        self.file_menu.addAction(self.add_scales_action)

        # Подключаем меню к кнопке
        self.btn_file.setMenu(self.file_menu)

        self.btn_settings = QtWidgets.QPushButton("Настройки")
        self.btn_settings.setFlat(True)  # Убираем стандартный вид кнопки

        # Создаем выпадающее меню для кнопки Настройки
        self.settings_menu = QtWidgets.QMenu(self.btn_settings)
        self.settings_menu.setStyleSheet("""
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
        self.scales_config_action = QtWidgets.QAction("Подключение к весам", self)
        self.scales_config_action.triggered.connect(self.system_clicked.emit)
        self.settings_menu.addAction(self.scales_config_action)

        self.printer_config_action = QtWidgets.QAction("Подключение к термопринтеру RD-V2", self)
        self.printer_config_action.triggered.connect(self.printer_config_clicked.emit)
        self.settings_menu.addAction(self.printer_config_action)

        # Кнопка управления пользователями убрана из меню настроек

        # Подключаем меню к кнопке
        self.btn_settings.setMenu(self.settings_menu)

        self.btn_help = QtWidgets.QPushButton("Справка")
        self.btn_help.setFlat(True)  # Убираем стандартный вид кнопки

        # Создаем выпадающее меню для кнопки Справка
        self.help_menu = QtWidgets.QMenu(self.btn_help)
        self.help_menu.setStyleSheet("""
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
        self.about_action = QtWidgets.QAction("О программе", self)
        self.about_action.triggered.connect(self.show_about_program)
        self.help_menu.addAction(self.about_action)

        self.license_action = QtWidgets.QAction("Лицензия", self)
        self.license_action.triggered.connect(self.show_license_info)
        self.help_menu.addAction(self.license_action)

        # Подключаем меню к кнопке
        self.btn_help.setMenu(self.help_menu)

        # Кнопка управления пользователями (только для админа)
        self.btn_user_management = QtWidgets.QPushButton("Управление пользователями")
        self.btn_user_management.setFlat(True)  # Убираем стандартный вид кнопки
        # Добавляем иконку
        user_management_icon = QtGui.QIcon("static/manage_group.svg")
        self.btn_user_management.setIcon(user_management_icon)
        self.btn_user_management.setIconSize(QtCore.QSize(20, 20))
        self.btn_user_management.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                text-decoration: none;
                font-size: 12pt;
                font-family: {header_font_family};
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #e5e7eb;
            }}
        """)
        self.btn_user_management.setVisible(False)  # по умолчанию скрыта
        self.btn_user_management.clicked.connect(self.user_management_clicked.emit)

        left_layout.addWidget(self.btn_file)
        left_layout.addWidget(self.btn_settings)
        left_layout.addWidget(self.btn_help)
        left_layout.addWidget(self.btn_user_management)

        # Кнопка удаления записи (только для админа)
        self.btn_delete_record = QtWidgets.QPushButton("Удалить запись")
        self.btn_delete_record.setFlat(True)  # Убираем стандартный вид кнопки
        # Добавляем иконку
        delete_icon = QtGui.QIcon("static/delete_str.svg")
        self.btn_delete_record.setIcon(delete_icon)
        self.btn_delete_record.setIconSize(QtCore.QSize(20, 20))
        self.btn_delete_record.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                text-decoration: none;
                font-size: 12pt;
                font-family: {header_font_family};
                padding: 8px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #e5e7eb;
            }}
        """)
        self.btn_delete_record.setVisible(False)  # по умолчанию скрыта
        self.btn_delete_record.clicked.connect(self.delete_record_clicked.emit)
        left_layout.addWidget(self.btn_delete_record)

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
        self.user_label.setStyleSheet(f"font-size: 11pt; margin-right: 0px; font-family: {header_font_family};")
        self.user_label.setVisible(False)  # по умолчанию скрыта
        right_layout.addWidget(self.user_label)

        self.user_button = QtWidgets.QPushButton("Войти")
        user_icon = QtGui.QIcon("static/user_icon.svg")
        # Увеличиваем размер иконки пользователя еще больше
        self.user_button.setIconSize(QtCore.QSize(40, 40))  # Максимальный размер иконки
        self.user_button.setIcon(user_icon)
        self.user_button.setStyleSheet(f"font-size: 11pt; margin-left: 0px; font-family: {header_font_family};")
        self.user_button.clicked.connect(self.login_clicked.emit)
        right_layout.addWidget(self.user_button)

        self.logout_button = QtWidgets.QPushButton("Завершить сеанс")
        self.logout_button.setStyleSheet(f"font-size: 11pt; font-family: {header_font_family};")
        logout_icon = QtGui.QIcon("static/logout.svg")
        self.logout_button.setIcon(logout_icon)
        self.logout_button.setIconSize(QtCore.QSize(32, 32))
        self.logout_button.clicked.connect(self.logout_clicked.emit)
        self.logout_button.setVisible(False)
        right_layout.addWidget(self.logout_button)

        top_layout.addWidget(right_widget, alignment=QtCore.Qt.AlignRight)

        header_label = QtWidgets.QLabel("ЖУРНАЛ ВЗВЕШИВАНИЙ")
        header_label.setStyleSheet(f"""
            background-color: #3a5c7e;
            color: white;
            padding: 8px 16px;
            font-size: 12pt;
            font-weight: 600;
            font-family: {header_font_family};
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
        <div style='text-align: left;'>
            <h3>О программе</h3>
            <p><b>Журнал взвешиваний 2.0</b></p>
            <p>Авторские права © Зуев А.Д.</p>
            <p>ПО "Журнал взвешиваний 2.0" предназначено для автоматизации процесса учета взвешивания грузов в складских, производственных и торговых помещениях.</p>
            <p>Локальное хранение всех взвешиваний на рабочем месте клиента.</p>
            <p><b>Серийный номер:</b> 10027/272B:2D065F22</p>
            <p><b>Используемое окружение:</b> Windows 10</p>
        </div>
        """

        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("О программе")
        msg_box.setText(about_text)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.setFixedSize(400, 200)
        msg_box.exec_()

    def show_license_info(self):
        """Показывает информацию о лицензии"""
        import license_manager
        from datetime import datetime

        license_info = license_manager.get_license_info()

        if license_info:
            activation_date = datetime.fromisoformat(license_info['activation_date'])
            formatted_date = activation_date.strftime("%d.%m.%Y %H:%M:%S")
            license_text = f"""
            <div style='text-align: left;'>
                <h3>Информация о лицензии</h3>
                <p><b>Статус лицензии:</b> Активирована</p>
                <p><b>Дата активации:</b> {formatted_date}</p>
                <p><b>Код активации:</b> {license_info['activation_code'][:16]}...</p>
                <p><b>UUID системы:</b> {license_info['system_uuid']}</p>
            </div>
            """
        else:
            system_uuid = license_manager.get_system_uuid()
            license_text = f"""
            <div style='text-align: left;'>
                <h3>Информация о лицензии</h3>
                <p><b>Статус лицензии:</b> Не активирована</p>
                <p><b>UUID системы:</b> {system_uuid}</p>
                <p>Для активации лицензии введите код активации при запуске программы.</p>
            </div>
            """

        # Используем обычное QDialog вместо QMessageBox для полного контроля размера
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Лицензия")
        dialog.setFixedSize(400, 200)

        layout = QtWidgets.QVBoxLayout(dialog)

        # Метка с текстом лицензии
        text_label = QtWidgets.QLabel(license_text)
        text_label.setWordWrap(True)
        text_label.setTextFormat(QtCore.Qt.RichText)
        layout.addWidget(text_label)

        # Кнопка OK
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        ok_button = QtWidgets.QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        dialog.exec_()

    def set_logged_in_user(self, username):
        self.logged_in_user = username
        # Не показываем информацию о пользователе в хедере
        self.user_label.setVisible(False)      # Скрываем "Пользователь:"
        self.user_button.setVisible(False)     # Скрываем кнопку пользователя
        self.logout_button.setVisible(True)

        # Показываем управление пользователями и удаление записей только для админа
        if username == "admin":
            self.btn_user_management.setVisible(True)
            self.btn_delete_record.setVisible(True)
        else:
            self.btn_user_management.setVisible(False)
            self.btn_delete_record.setVisible(False)

    def logout(self):
        self.logged_in_user = None
        self.user_label.setVisible(False)     # Скрываем "Пользователь:"
        self.user_button.setVisible(True)     # Показываем кнопку войти
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
        # Скрываем управление пользователями и удаление записей при выходе
        self.btn_user_management.setVisible(False)
        self.btn_delete_record.setVisible(False)
