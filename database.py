import sqlite3
import logging
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtSerialPort import QSerialPortInfo
from logger import get_logger

# Настройка логирования для database модуля
logger = get_logger('database')


DB_FILE = 'weights_journal.db'


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS com_configurations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            port TEXT NOT NULL,
            baud INTEGER NOT NULL,
            protocol INTEGER DEFAULT 1
        )
    ''')
    # Миграция: добавляем колонку protocol, если её нет
    try:
        cursor.execute("PRAGMA table_info(com_configurations)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'protocol' not in cols:
            cursor.execute("ALTER TABLE com_configurations ADD COLUMN protocol INTEGER DEFAULT 1")
    except Exception:
        pass
    
    # Создаем таблицу для хранения данных взвешиваний
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weighings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT NOT NULL,
            weight INTEGER NOT NULL,
            operator TEXT NOT NULL,
            weighing_mode TEXT DEFAULT '-',
            cargo_name TEXT DEFAULT '-',
            sender TEXT DEFAULT '-',
            recipient TEXT DEFAULT '-',
            comment TEXT DEFAULT '-',
            scales_name TEXT DEFAULT '-'
        )
    ''')

    # Миграция: удаляем колонку warehouse_number из таблицы weighings
    try:
        cursor.execute("PRAGMA table_info(weighings)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'warehouse_number' in cols:
            # Создаем новую таблицу без колонки warehouse_number
            cursor.execute('''
                CREATE TABLE weighings_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datetime TEXT NOT NULL,
                    weight INTEGER NOT NULL,
                    operator TEXT NOT NULL,
                    weighing_mode TEXT DEFAULT '-',
                    cargo_name TEXT DEFAULT '-',
                    sender TEXT DEFAULT '-',
                    recipient TEXT DEFAULT '-',
                    comment TEXT DEFAULT '-',
                    scales_name TEXT DEFAULT '-'
                )
            ''')

            # Копируем данные из старой таблицы в новую
            cursor.execute('''
                INSERT INTO weighings_new (id, datetime, weight, operator, weighing_mode, cargo_name,
                                         sender, recipient, comment, scales_name)
                SELECT id, datetime, weight, operator, weighing_mode, cargo_name,
                       sender, recipient, comment, scales_name
                FROM weighings
            ''')

            # Удаляем старую таблицу
            cursor.execute('DROP TABLE weighings')

            # Переименовываем новую таблицу
            cursor.execute('ALTER TABLE weighings_new RENAME TO weighings')

    except Exception as e:
        logger.error(f"Ошибка миграции базы данных: {e}")
    conn.commit()
    conn.close()


class ComConfigDialog(QtWidgets.QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("Настройка COM-порта")
        self.resize(600, 300)

        main_layout = QtWidgets.QVBoxLayout(self)

        config_layout = QtWidgets.QHBoxLayout()
        config_layout.addWidget(QtWidgets.QLabel("Имя конфигурации:"))
        self.name_edit = QtWidgets.QLineEdit()
        config_layout.addWidget(self.name_edit)

        config_layout.addWidget(QtWidgets.QLabel("COM порт:"))
        self.port_combo = QtWidgets.QComboBox()
        config_layout.addWidget(self.port_combo)

        config_layout.addWidget(QtWidgets.QLabel("Бадрейт:"))
        self.baud_combo = QtWidgets.QComboBox()
        common_bauds = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
        self.baud_combo.addItems(common_bauds)
        config_layout.addWidget(self.baud_combo)

        # Протокол обмена
        config_layout.addWidget(QtWidgets.QLabel("Протокол:"))
        self.protocol_combo = QtWidgets.QComboBox()
        self.protocol_combo.addItems(["1", "2"])  # 1: "ww005kg", 2: "ST, GS,+000005 kg"
        config_layout.addWidget(self.protocol_combo)

        main_layout.addLayout(config_layout)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Добавить")
        self.delete_button = QtWidgets.QPushButton("Удалить выбранную")
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Имя конфигурации", "COM порт", "Бадрейт", "Протокол"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        main_layout.addWidget(self.table)

        # Устанавливаем стиль таблицы с синим выделением
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

        self.update_com_ports()
        self.load_configurations()

        self.add_button.clicked.connect(self.add_configuration)
        self.delete_button.clicked.connect(self.delete_selected_configuration)

    def update_com_ports(self):
        self.port_combo.clear()
        ports = QSerialPortInfo.availablePorts()
        port_names = [port.portName() for port in ports]
        self.port_combo.addItems(port_names)

    def load_configurations(self):
        self.table.setRowCount(0)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, port, baud, COALESCE(protocol, 1)
            FROM com_configurations
            WHERE username=?
            ORDER BY id DESC
        ''', (self.username,))
        rows = cursor.fetchall()
        conn.close()

        for row_data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate(row_data):
                self.table.setItem(row, col, QtWidgets.QTableWidgetItem(str(val)))

        # Автоматическая подстройка ширины всех столбцов под содержимое
        for col in range(self.table.columnCount()):
            self.table.resizeColumnToContents(col)

    def add_configuration(self):
        name = self.name_edit.text().strip()
        port = self.port_combo.currentText()
        baud = int(self.baud_combo.currentText())
        protocol = int(self.protocol_combo.currentText()) if self.protocol_combo.currentText().isdigit() else 1

        if not name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя конфигурации")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO com_configurations (username, name, port, baud, protocol)
            VALUES (?, ?, ?, ?, ?)
        ''', (self.username, name, port, baud, protocol))
        conn.commit()
        conn.close()

        self.name_edit.clear()
        self.load_configurations()

    def delete_selected_configuration(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for index in sorted(selected, reverse=True):
            name = self.table.item(index.row(), 0).text()
            port = self.table.item(index.row(), 1).text()
            baud = int(self.table.item(index.row(), 2).text())
            protocol_text = self.table.item(index.row(), 3)
            protocol = int(protocol_text.text()) if protocol_text and protocol_text.text().isdigit() else 1

            cursor.execute('''
                DELETE FROM com_configurations
                WHERE username=? AND name=? AND port=? AND baud=? AND COALESCE(protocol,1)=?
            ''', (self.username, name, port, baud, protocol))
            self.table.removeRow(index.row())

        conn.commit()
        conn.close()


def save_weighing(datetime_str, weight, operator, weighing_mode='-', cargo_name='-',
                  sender='-', recipient='-', comment='-', scales_name='-'):
    """
    Сохраняет данные взвешивания в базу данных
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO weighings (datetime, weight, operator, weighing_mode, cargo_name,
                             sender, recipient, comment, scales_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (datetime_str, weight, operator, weighing_mode, cargo_name,
          sender, recipient, comment, scales_name))
    conn.commit()
    conn.close()


def get_weighings(operator=None):
    """
    Получает данные взвешиваний из базы данных
    Если operator указан и не "admin", возвращает только записи этого оператора
    Для admin возвращает все записи
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if operator == "admin":
        # Admin видит все записи
        cursor.execute('''
            SELECT datetime, weight, operator, weighing_mode, cargo_name,
                   sender, recipient, comment, scales_name
            FROM weighings
            ORDER BY id DESC
        ''')
    elif operator:
        cursor.execute('''
            SELECT datetime, weight, operator, weighing_mode, cargo_name,
                   sender, recipient, comment, scales_name
            FROM weighings
            WHERE operator = ?
            ORDER BY id DESC
        ''', (operator,))
    else:
        cursor.execute('''
            SELECT datetime, weight, operator, weighing_mode, cargo_name,
                   sender, recipient, comment, scales_name
            FROM weighings
            ORDER BY id DESC
        ''')

    rows = cursor.fetchall()
    conn.close()
    return rows


# Вызовите один раз в начале приложения
init_db()
