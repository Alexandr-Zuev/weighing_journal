import sqlite3
from PyQt5 import QtWidgets
from PyQt5.QtSerialPort import QSerialPortInfo

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
    # Миграция: добавление protocol при необходимости
    try:
        cursor.execute("PRAGMA table_info(com_configurations)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'protocol' not in cols:
            cursor.execute("ALTER TABLE com_configurations ADD COLUMN protocol INTEGER DEFAULT 1")
    except Exception:
        pass
    conn.commit()
    conn.close()

class ComConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, username=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("Настройка COM-порта")
        self.setFixedSize(600, 300)

        main_layout = QtWidgets.QVBoxLayout(self)

        # Конфигурации
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
        self.protocol_combo.addItems(["1", "2"])  # 1: ww005kg, 2: ST,GS,+000005kg
        config_layout.addWidget(self.protocol_combo)

        main_layout.addLayout(config_layout)

        # Кнопки
        buttons_layout = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Добавить")
        self.delete_button = QtWidgets.QPushButton("Удалить выбранную")
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        # Таблица конфигураций
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Имя конфигурации", "COM порт", "Бадрейт", "Протокол"])
        # Все столбцы одинаковой ширины
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        main_layout.addWidget(self.table)

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
        if not self.username:
            return
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

        # Ширины столбцов остаются равными благодаря режиму Stretch

    def add_configuration(self):
        name = self.name_edit.text().strip()
        port = self.port_combo.currentText()
        baud = int(self.baud_combo.currentText())
        protocol = int(self.protocol_combo.currentText()) if self.protocol_combo.currentText().isdigit() else 1

        if not name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите имя конфигурации")
            return

        if not self.username:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Пользователь не задан")
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

        if not self.username:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Пользователь не задан")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for index in sorted(selected, reverse=True):
            name = self.table.item(index.row(), 0).text()
            port = self.table.item(index.row(), 1).text()
            baud = int(self.table.item(index.row(), 2).text())
            protocol_item = self.table.item(index.row(), 3)
            protocol = int(protocol_item.text()) if protocol_item and protocol_item.text().isdigit() else 1

            cursor.execute('''
                DELETE FROM com_configurations
                WHERE username=? AND name=? AND port=? AND baud=? AND COALESCE(protocol,1)=?
            ''', (self.username, name, port, baud, protocol))
            self.table.removeRow(index.row())

        conn.commit()
        conn.close()

init_db()
