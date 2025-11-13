from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime as dt
from database import get_weighings
import sqlite3


class LeftPanelWidget(QtWidgets.QWidget):
    summary_changed = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.all_weighings = []  # хранит полные данные до фильтрации
        self.is_admin = False  # флаг для определения, является ли пользователь админом

        main_layout = QtWidgets.QVBoxLayout(self)

        # Заголовок журнала взвешиваний
        self.title_label = QtWidgets.QLabel("ЖУРНАЛ ВЗВЕШИВАНИЙ")
        self.title_label.setStyleSheet("""
            background-color: #3a5c7e;
            color: white;
            padding: 8px 16px;
            font-size: 12pt;
            font-weight: 600;
        """)
        self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        main_layout.addWidget(self.title_label)

        # Блок фильтра
        filter_widget = QtWidgets.QWidget()
        filter_widget.setStyleSheet("background-color: #f3f4f6;")
        filter_layout = QtWidgets.QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(16, 8, 16, 8)
        filter_layout.setSpacing(10)
        filter_layout.setAlignment(QtCore.Qt.AlignLeft)

        filter_icon = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap("static/filter.svg")
        filter_icon.setPixmap(
            pixmap.scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        )
        filter_layout.addWidget(filter_icon)

        filter_label = QtWidgets.QLabel("ФИЛЬТР")
        filter_label.setStyleSheet("font-weight: 600;")
        filter_layout.addWidget(filter_label)

        inputs_widget = QtWidgets.QWidget()
        inputs_layout = QtWidgets.QHBoxLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(8)
        inputs_layout.setAlignment(QtCore.Qt.AlignVCenter)

        self.filter_checkbox = QtWidgets.QCheckBox()
        self.filter_checkbox.setStyleSheet("margin-left: 0px; margin-right: 6px; padding: 0;")
        self.filter_checkbox.setChecked(False)
        inputs_layout.addWidget(self.filter_checkbox)

        date_label = QtWidgets.QLabel("ДАТА/ВРЕМЯ")
        date_label.setStyleSheet("margin-left: 0px;")
        inputs_layout.addWidget(date_label)

        self.date_edit1 = QtWidgets.QDateEdit()
        self.date_edit1.setCalendarPopup(True)
        self.date_edit1.setDisplayFormat("dd.MM.yyyy")
        self.date_edit1.setFixedWidth(110)
        self.date_edit1.setDate(QtCore.QDate.currentDate())
        inputs_layout.addWidget(self.date_edit1)

        self.time_edit1 = QtWidgets.QTimeEdit()
        self.time_edit1.setDisplayFormat("HH:mm")
        self.time_edit1.setFixedWidth(70)
        self.time_edit1.setTime(QtCore.QTime(0, 0))
        inputs_layout.addWidget(self.time_edit1)

        dash_label = QtWidgets.QLabel("-")
        inputs_layout.addWidget(dash_label)

        self.date_edit2 = QtWidgets.QDateEdit()
        self.date_edit2.setCalendarPopup(True)
        self.date_edit2.setDisplayFormat("dd.MM.yyyy")
        self.date_edit2.setFixedWidth(110)
        self.date_edit2.setDate(QtCore.QDate.currentDate())
        inputs_layout.addWidget(self.date_edit2)

        self.time_edit2 = QtWidgets.QTimeEdit()
        self.time_edit2.setDisplayFormat("HH:mm")
        self.time_edit2.setFixedWidth(70)
        self.time_edit2.setTime(QtCore.QTime(23, 59))
        inputs_layout.addWidget(self.time_edit2)

        # Фильтр по режиму взвешивания (сгруппирован: чекбокс + название + меню)
        mode_widget = QtWidgets.QWidget()
        mode_widget.setStyleSheet("background: transparent; border: none;")
        mode_layout = QtWidgets.QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(4)

        self.mode_checkbox = QtWidgets.QCheckBox()
        self.mode_checkbox.setStyleSheet("margin-left: 0px; margin-right: 6px; padding: 0;")
        self.mode_checkbox.setChecked(False)
        mode_layout.addWidget(self.mode_checkbox)

        mode_label = QtWidgets.QLabel("РЕЖИМ ВЗВЕШИВАНИЯ")
        mode_label.setStyleSheet("margin-left: 0px;")
        mode_layout.addWidget(mode_label)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["Все", "Ручное", "Автоматическое"])
        self.mode_combo.setStyleSheet(
            "QComboBox {"
            "  background: white; color: #111827; padding: 2px 6px;"
            "  border: 1px solid #9ca3af; border-radius: 4px;"
            "}"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView {"
            "  background: white; color: #111827;"
            "  selection-background-color: #e5e7eb; selection-color: #111827;"
            "  outline: none;"
            "}"
        )
        mode_layout.addWidget(self.mode_combo)

        inputs_layout.addWidget(mode_widget)

        # Сигналы изменения фильтров
        self.filter_checkbox.stateChanged.connect(self.apply_filters)
        self.date_edit1.dateChanged.connect(self.apply_filters)
        self.time_edit1.timeChanged.connect(self.apply_filters)
        self.date_edit2.dateChanged.connect(self.apply_filters)
        self.time_edit2.timeChanged.connect(self.apply_filters)
        self.mode_checkbox.stateChanged.connect(self.apply_filters)
        self.mode_combo.currentIndexChanged.connect(self.apply_filters)

        filter_layout.addWidget(inputs_widget)
        main_layout.addWidget(filter_widget)

        # Создаем стек виджетов для переключения между таблицей и сообщением
        self.stacked_widget = QtWidgets.QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Создаем виджет с сообщением о необходимости входа в систему
        self.login_message_widget = QtWidgets.QWidget()
        login_message_layout = QtWidgets.QVBoxLayout(self.login_message_widget)
        login_message_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        login_message_label = QtWidgets.QLabel("Войдите в систему для просмотра данных взвешиваний")
        login_message_label.setAlignment(QtCore.Qt.AlignCenter)
        login_message_label.setStyleSheet("""
            font-size: 14pt;
            color: #6b7280;
            padding: 40px;
        """)
        login_message_layout.addWidget(login_message_label)
        
        # Создаем виджет с таблицей
        self.table_widget = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # Таблица
        self.table = QtWidgets.QTableWidget()
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # Запрещаем редактирование таблицы (будет включено для админа)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # Реакция на выделение строк для обновления сводки
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        # Обработчик для сохранения изменений в базе данных (только для админа)
        self.table.itemChanged.connect(self.on_item_changed)
        # Устанавливаем политику размера для полного заполнения блока
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        table_layout.addWidget(self.table)

        headers = [
            "Дата/Время",
            "Масса",
            "ВЕСЫ№",
            "Оператор",
            "Режим взвешивания",
            "Наименование груза",
            "Отправитель",
            "Получатель",
            "Примечание",
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        self.table.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 10pt;
                font-family: Calibri;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                font-family: Calibri;
                font-size: 11pt;
                background-image: url(static/logo_nv.png);
                background-repeat: no-repeat;
                background-position: center center;
                background-attachment: fixed;
                background-color: rgba(255, 255, 255, 0.5);
            }
            QTableWidget::item {
                padding: 4px;
                background-color: rgba(255, 255, 255, 0.85);
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)

        # Настраиваем заголовки таблицы после установки стиля
        header = self.table.horizontalHeader()
        if header:
            # Включаем возможность ручного изменения ширины столбцов
            header.setSectionsMovable(True)
            header.setSectionsClickable(True)
            # Устанавливаем интерактивный режим для ручного изменения ширины
            header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

            # Устанавливаем последний столбец в режим растяжения для заполнения всей ширины блока
            last_column_index = len(headers) - 1
            header.setSectionResizeMode(last_column_index, QtWidgets.QHeaderView.Stretch)

            # Увеличиваем шрифт заголовков
            header_font = header.font()
            header_font.setPointSize(12)
            header_font.setBold(True)
            header.setFont(header_font)

            # Устанавливаем ширину столбцов по содержимому заголовков как начальную
            self.table.resizeColumnsToContents()

            # Устанавливаем разумную минимальную ширину для возможности уменьшения столбцов
            header.setMinimumSectionSize(30)

        vertical_header = self.table.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)

        # Добавляем виджеты в стек
        self.stacked_widget.addWidget(self.login_message_widget)  # Индекс 0
        self.stacked_widget.addWidget(self.table_widget)         # Индекс 1

        # По умолчанию показываем сообщение о необходимости входа
        self.stacked_widget.setCurrentIndex(0)

        # Флаг для предотвращения рекурсии при обновлении таблицы
        self.updating_table = False

    def set_current_user(self, username):
        """Устанавливает текущего пользователя и обновляет отображение"""
        self.current_user = username
        self.is_admin = (username == "admin")
        if username:
            self.stacked_widget.setCurrentIndex(1)  # Показываем таблицу
            # Для админа разрешаем редактирование
            if self.is_admin:
                self.table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
            else:
                self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.load_weighings_data()
        else:
            self.stacked_widget.setCurrentIndex(0)  # Показываем сообщение о входе
            self.is_admin = False

    def load_weighings_data(self):
        """Загружает данные взвешиваний из базы данных в таблицу"""
        if not self.current_user:
            self.table.setRowCount(0)
            self.summary_changed.emit("Войдите для просмотра записей")
            return
            
        try:
            self.all_weighings = get_weighings(operator=self.current_user)
            self.apply_filters()
        except Exception as e:
            print(f"Ошибка при загрузке данных взвешиваний: {e}")
            # В случае ошибки показываем пустую таблицу
            self.table.setRowCount(0)
            self.summary_changed.emit("Ошибка загрузки данных")

    def apply_filters(self):
        """Применяет фильтры к self.all_weighings и рендерит таблицу"""
        filtered = list(self.all_weighings)

        # Фильтр по режиму (включается галочкой)
        if self.mode_checkbox.isChecked():
            mode = self.mode_combo.currentText() if hasattr(self, 'mode_combo') else "Все"
            if mode != "Все":
                filtered = [w for w in filtered if (w[3] or "-") == mode]

        # Фильтр по дате/времени
        if self.filter_checkbox.isChecked():
            start_dt = self._get_start_dt()
            end_dt = self._get_end_dt()
            def in_range(w):
                try:
                    wdt = dt.strptime(w[0], "%d.%m.%Y %H:%M")
                except Exception:
                    return False
                return (wdt >= start_dt) and (wdt <= end_dt)
            filtered = [w for w in filtered if in_range(w)]

        # Фильтр по получателю удален

        self._render_table(filtered, total_all=len(self.all_weighings))

    def _render_table(self, weighings, total_all=None):
        self.updating_table = True
        self.table.setRowCount(len(weighings))
        self.displayed_weighings = weighings  # сохраняем для редактирования
        headers = [
            "Дата/Время",
            "Масса",
            "ВЕСЫ№",
            "Оператор",
            "Режим взвешивания",
            "Наименование груза",
            "Отправитель",
            "Получатель",
            "Примечание",
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        for row_idx, w in enumerate(weighings):
            datetime_str, weight, operator, weighing_mode, cargo_name, sender, recipient, comment, scales_name = w
            row_data = [
                datetime_str,
                f"{weight} кг",
                scales_name or "-",
                operator,
                weighing_mode,
                cargo_name,
                sender,
                recipient,
                comment
            ]
            for col_idx, item in enumerate(row_data):
                table_item = QtWidgets.QTableWidgetItem(str(item))
                self.table.setItem(row_idx, col_idx, table_item)

        self.updating_table = False
        displayed = len(weighings)
        total = total_all if total_all is not None else displayed
        status_text = f"Отображаются записи: {displayed} из {total}, выбрано: 0"
        self.summary_changed.emit(status_text)

    def on_selection_changed(self):
        total = self.table.rowCount()
        # Подсчитываем уникальные выделенные строки
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        selected_count = len(selected_rows)
        # total_all = общее без учета фильтра
        total_all = len(self.all_weighings) if self.all_weighings is not None else total
        status_text = f"Отображаются записи: {total} из {total_all}, выбрано: {selected_count}"
        self.summary_changed.emit(status_text)

    def _get_start_dt(self) -> dt:
        date = self.date_edit1.date()
        time = self.time_edit1.time()
        return dt(
            date.year(), date.month(), date.day(),
            time.hour(), time.minute()
        )

    def _get_end_dt(self) -> dt:
        date = self.date_edit2.date()
        time = self.time_edit2.time()
        return dt(
            date.year(), date.month(), date.day(),
            time.hour(), time.minute()
        )

    def refresh_weighings_data(self):
        """Обновляет данные в таблице (вызывается при добавлении нового взвешивания)"""
        self.load_weighings_data()

    def on_item_changed(self, item):
        """Обработчик изменения ячейки таблицы (только для админа)"""
        if not self.is_admin or self.updating_table:
            return

        row = item.row()
        col = item.column()
        new_value = item.text()

        # Получаем оригинальные данные для обновления в БД
        if hasattr(self, 'displayed_weighings') and row < len(self.displayed_weighings):
            original_row = self.displayed_weighings[row]
            # original_row: (datetime, weight, operator, weighing_mode, cargo_name, sender, recipient, comment, scales_name)

            # Определяем, какое поле обновляем
            field_map = {
                0: 'datetime',
                1: 'weight',
                2: 'operator',
                3: 'weighing_mode',
                4: 'cargo_name',
                5: 'sender',
                6: 'recipient',
                7: 'comment',
                8: 'scales_name'
            }

            if col in field_map:
                field = field_map[col]
                # Получаем ID записи для обновления
                conn = sqlite3.connect('weights_journal.db')
                cursor = conn.cursor()

                # Найти ID по оригинальным данным
                cursor.execute('''
                    SELECT id FROM weighings
                    WHERE datetime=? AND weight=? AND operator=?
                ''', (original_row[0], original_row[1], original_row[2]))

                result = cursor.fetchone()
                if result:
                    record_id = result[0]
                    # Обновляем поле
                    cursor.execute(f'UPDATE weighings SET {field}=? WHERE id=?', (new_value, record_id))
                    conn.commit()
                    print(f"Обновлено поле {field} для записи ID {record_id}: {new_value}")
                else:
                    print("Не удалось найти запись для обновления")

                conn.close()
