import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import QtPrintSupport
from header import HeaderWidget
from left_panel import LeftPanelWidget
from scales_manager import ScalesManager
from footer import FooterWidget
from com_config_dialog import ComConfigDialog
from login_dialog import LoginDialog
from thermal_printer_manager import ThermalPrinterManager
from thermal_printer_dialog import ThermalPrinterDialog
from user_management_dialog import UserManagementDialog
import csv
from datetime import datetime
import license_manager
from activation_dialog import ActivationDialog


class WeighingJournal(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Журнал взвешиваний")
        self.resize(1300, 820)

        # Проверка лицензии
        if not license_manager.is_license_valid():
            activation_dialog = ActivationDialog()
            result = activation_dialog.exec_()
            if result != QtWidgets.QDialog.Accepted:
                sys.exit(1)

        font_id = QtGui.QFontDatabase.addApplicationFont("static/DSEG7Classic-Regular.ttf")
        font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
        font_family = font_families[0] if font_families else "Arial"

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        self.header = HeaderWidget()
        main_layout.addWidget(self.header)

        h_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(h_layout)

        self.left_panel = LeftPanelWidget()
        h_layout.addWidget(self.left_panel, stretch=1)

        self.scales_manager = ScalesManager(font_family=font_family)
        # Фиксированная минимальная ширина для правой панели
        self.scales_manager.setMinimumWidth(450)
        h_layout.addWidget(self.scales_manager, stretch=0)

        self.footer = FooterWidget()
        main_layout.addWidget(self.footer)

        self.current_user = None

        # Инициализация менеджера термопринтера
        self.printer_manager = ThermalPrinterManager()

        # Передаем printer_manager в scales_manager
        self.scales_manager.printer_manager = self.printer_manager

        # Подключение сигналов из HeaderWidget
        self.header.system_clicked.connect(self.open_com_config_dialog)
        self.header.printer_config_clicked.connect(self.open_printer_config_dialog)
        self.header.login_clicked.connect(self.open_login_dialog)
        self.header.logout_clicked.connect(self.on_logout)
        self.header.add_scales_clicked.connect(self.add_new_scales)
        self.header.user_management_clicked.connect(self.open_user_management_dialog)
        self.header.delete_record_clicked.connect(self.on_delete_record)
        
        # Подключение сигнала сохранения взвешивания к обновлению таблицы
        self.scales_manager.weighing_saved.connect(self.left_panel.refresh_weighings_data)

        # Связываем сводку и пользователя с футером
        self.left_panel.summary_changed.connect(self.footer.set_status_text)
        self.footer.set_user(self.current_user)

        # Действия футера
        self.footer.print_clicked.connect(self.on_footer_print)
        self.footer.receipt_print_clicked.connect(self.on_footer_receipt_print)
        self.footer.export_clicked.connect(self.on_footer_export)
        self.footer.report_clicked.connect(self.on_footer_report)

    def add_new_scales(self):
        """Добавляет новые весы в интерфейс"""
        self.scales_manager.add_scales()

    def on_footer_print(self):
        # Формирование акта взвешивания (PDF) - альбомная ориентация
        import tempfile
        import os
        import subprocess

        # Проверяем, выделена ли ровно 1 строка в таблице
        table = self.left_panel.table
        selected_rows = table.selectionModel().selectedRows() if table.selectionModel() else []

        if len(selected_rows) != 1:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите ровно одну строку для формирования акта взвешивания!")
            return

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name

        printer = QtPrintSupport.QPrinter()
        printer.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat)
        printer.setOutputFileName(temp_path)
        printer.setPageSize(QtPrintSupport.QPrinter.A4)
        printer.setOrientation(QtPrintSupport.QPrinter.Landscape)  # Альбомная ориентация
        printer.setPageMargins(10, 10, 10, 10, QtPrintSupport.QPrinter.Millimeter)

        painter = QtGui.QPainter(printer)
        try:
            self._draw_invoice(painter, printer)
        finally:
            painter.end()

        # Открываем PDF файл в системном просмотрщике
        try:
            if os.name == 'nt':  # Windows
                os.startfile(temp_path)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.run(['xdg-open', temp_path], check=False)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Ошибка", f"Не удалось открыть PDF файл: {str(e)}")
            # В случае ошибки открытия, показываем диалог сохранения
            save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Сохранить акт взвешивания", "akt_vzveshivaniya.pdf", "PDF (*.pdf)"
            )
            if save_path:
                import shutil
                shutil.copy2(temp_path, save_path)
                QtWidgets.QMessageBox.information(self, "PDF сохранен", f"Файл сохранен: {save_path}")

        # Удаляем временный файл через некоторое время (асинхронно)
        import threading
        def cleanup_temp_file():
            import time
            time.sleep(5)  # Даем время на открытие файла
            try:
                os.unlink(temp_path)
            except:
                pass  # Игнорируем ошибки удаления

        threading.Thread(target=cleanup_temp_file, daemon=True).start()

    def _draw_invoice(self, painter: QtGui.QPainter, printer: QtPrintSupport.QPrinter):
        # Геометрия страницы
        rect = printer.pageRect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

        # Шрифты
        font_title = QtGui.QFont("Arial", 14, QtGui.QFont.Bold)
        font_normal = QtGui.QFont("Arial", 10)
        font_small = QtGui.QFont("Arial", 8)
        font_table = QtGui.QFont("Arial", 9)

        # Верхний заголовок "АКТ ВЗВЕШИВАНИЯ"
        painter.setFont(font_title)
        title = "АКТ ВЗВЕШИВАНИЯ"
        painter.drawText(x + 30, y + 30, w - 60, 25, QtCore.Qt.AlignCenter, title)

        # Линия под заголовком
        painter.drawLine(x + 30, y + 55, w - 30, y + 55)

        # Получаем данные из выбранной строки таблицы
        table = self.left_panel.table
        selected_rows = table.selectionModel().selectedRows() if table.selectionModel() else []
        if selected_rows:
            row_index = selected_rows[0].row()
        else:
            current = table.currentRow()
            row_index = current if current >= 0 else 0

        def get_table_value(col):
            item = table.item(row_index, col)
            return item.text() if item else ""

        # Данные из таблицы
        datetime_val = get_table_value(0)
        weight_val = get_table_value(1)
        operator_val = get_table_value(2)
        mode_val = get_table_value(3)
        name_val = get_table_value(4)
        warehouse_val = get_table_value(5)
        sender_val = get_table_value(6)
        receiver_val = get_table_value(7)
        notes_val = get_table_value(8)

        # Левая колонка - отправитель
        painter.setFont(font_normal)
        left_x = x + 30
        line_height = 20

        painter.drawText(left_x, y + 75, 150, line_height, QtCore.Qt.AlignLeft, "Отправитель:")
        painter.drawText(left_x, y + 95, 150, line_height, QtCore.Qt.AlignLeft, "Адрес:")
        painter.drawText(left_x, y + 115, 150, line_height, QtCore.Qt.AlignLeft, "Телефон:")

        # Правая колонка - получатель
        right_x = int(x + w/2 + 30)
        painter.drawText(right_x, y + 75, 150, line_height, QtCore.Qt.AlignLeft, "Получатель:")
        painter.drawText(right_x, y + 95, 150, line_height, QtCore.Qt.AlignLeft, "Адрес:")
        painter.drawText(right_x, y + 115, 150, line_height, QtCore.Qt.AlignLeft, "Телефон:")

        # Нижняя часть - места для подписей
        bottom_y = h - 120
        painter.setFont(font_normal)

        # Заголовок для подписей
        painter.drawText(x + 30, bottom_y, w - 60, 20, QtCore.Qt.AlignCenter,
                        "Подписи ответственных лиц:")

        # Первая подпись - отправитель
        painter.drawText(x + 50, bottom_y + 25, 200, 20, QtCore.Qt.AlignLeft,
                        "Представитель отправителя:")
        painter.drawLine(x + 200, bottom_y + 40, x + 400, bottom_y + 40)

        # Вторая подпись - получатель
        painter.drawText(x + 450, bottom_y + 25, 200, 20, QtCore.Qt.AlignLeft,
                        "Представитель получателя:")
        painter.drawLine(x + 600, bottom_y + 40, w - 50, bottom_y + 40)

        # Третья подпись - организация
        painter.drawText(x + 50, bottom_y + 55, 300, 20, QtCore.Qt.AlignLeft,
                        "Организация, проводящая взвешивание:")
        painter.drawLine(x + 300, bottom_y + 70, w - 50, bottom_y + 70)

        # Линии под полями
        painter.drawLine(x + 30, y + 135, w - 30, y + 135)

        # Таблица журнала взвешиваний
        painter.setFont(font_normal)
        table_y = y + 145

        # Получаем заголовки из таблицы, исключая столбец "Режим"
        table = self.left_panel.table
        headers = []
        for i in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(i)
            if header_item:
                header_text = header_item.text()
                # Пропускаем столбец "Режим"
                if header_text != "Режим":
                    headers.append(header_text)
            else:
                headers.append(f"Колонка {i+1}")

        # Ширина колонок динамически
        if headers:
            total_width = w - 60  # Оставляем отступы
            col_width = total_width // len(headers)
            col_widths = [col_width] * len(headers)
            # Корректировка последней колонки
            col_widths[-1] = total_width - sum(col_widths[:-1])
        else:
            col_widths = []

        col_x = [x + 30]
        for width in col_widths:
            col_x.append(col_x[-1] + width)

        # Заголовки таблицы
        painter.drawRect(x + 30, table_y, sum(col_widths), 25)
        for i, header in enumerate(headers):
            painter.drawLine(col_x[i], table_y, col_x[i], table_y + 25)
            painter.drawText(col_x[i] + 2, table_y, col_widths[i] - 4, 25,
                           QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, header)
        painter.drawLine(col_x[-1], table_y, col_x[-1], table_y + 25)

        # Данные из таблицы левой панели - только выделенная строка
        startY = table_y + 25
        table_h = 25  # Только одна строка

        # Определяем индекс строки: при наличии выделения берем первую выделенную строку,
        # иначе используем текущую строку, если нет — 0
        selected_rows = table.selectionModel().selectedRows() if table.selectionModel() else []
        if selected_rows:
            row_index = selected_rows[0].row()
        else:
            current = table.currentRow()
            row_index = current if current >= 0 else 0

        # Рисуем строку таблицы
        painter.setFont(font_table)
        row_y = startY
        painter.drawRect(x + 30, row_y, sum(col_widths), 25)
        for i in range(len(col_x)):
            painter.drawLine(col_x[i], row_y, col_x[i], row_y + 25)

        # Заполняем ячейки данными из выделенной строки, пропуская столбец "Режим"
        header_index = 0
        for c in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(c)
            if header_item and header_item.text() == "Режим":
                continue  # Пропускаем столбец "Режим"

            item = table.item(row_index, c)
            cell_text = item.text() if item else ""
            painter.drawText(col_x[header_index] + 2, row_y, col_widths[header_index] - 4, 25,
                           QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, cell_text)
            header_index += 1
        painter.drawLine(col_x[-1], row_y, col_x[-1], row_y + 25)
    def on_footer_export(self):
        # Экспорт текущей таблицы в CSV
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить как", "weighings.csv", "CSV (*.csv)")
        if not path:
            return
        table = self.left_panel.table
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
                writer.writerow(headers)
                for row in range(table.rowCount()):
                    row_vals = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_vals.append(item.text() if item else '')
                    writer.writerow(row_vals)
            QtWidgets.QMessageBox.information(self, "Экспорт", "Данные успешно экспортированы в CSV.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def on_footer_receipt_print(self):
        """Печать чека из выделенной строки"""
        table = self.left_panel.table

        # Получить индекс выделенной строки (или текущей строки)
        selected_rows = table.selectionModel().selectedRows() if table.selectionModel() else []
        if selected_rows:
            row_index = selected_rows[0].row()
        else:
            current = table.currentRow()
            if current < 0:
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите строку для печати чека!")
                return
            row_index = current

        # Собрать данные из строки
        receipt_data = {}
        headers = []
        for col in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(col)
            if header_item:
                headers.append(header_item.text())

        for col in range(table.columnCount()):
            item = table.item(row_index, col)
            value = item.text() if item else ""
            header = headers[col] if col < len(headers) else f"Колонка_{col}"

            # Маппинг заголовков на ключи данных чека
            header_mapping = {
                "Дата/Время": "datetime",
                "Вес": "weight",
                "Оператор": "operator",
                "Режим": "mode",
                "Наименование": "name",
                "Склад": "warehouse",
                "Отпр.": "sender",
                "Получ.": "receiver",
                "Примечание": "notes"
            }

            key = header_mapping.get(header, header.lower().replace(" ", "_"))
            receipt_data[key] = value

        # Распечатать чек
        success, message = self.printer_manager.print_receipt(receipt_data)
        if success:
            QtWidgets.QMessageBox.information(self, "Успех", message)
        else:
            QtWidgets.QMessageBox.critical(self, "Ошибка", message)

    def on_footer_report(self):
        # Простой отчет: количество записей и диапазон дат
        table = self.left_panel.table
        count = table.rowCount()
        dates = []
        for row in range(count):
            item = table.item(row, 0)
            if item:
                dates.append(item.text())
        date_range = "-"
        if dates:
            first = min(dates)
            last = max(dates)
            date_range = f"{first} — {last}"
        QtWidgets.QMessageBox.information(self, "Отчет", f"Записей: {count}\nДиапазон дат: {date_range}")

    def open_com_config_dialog(self):
        if not self.current_user:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Для настройки COM-порта необходимо авторизоваться.")
            return
        dialog = ComConfigDialog(parent=self, username=self.current_user)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            config_name = dialog.name_edit.text()
            com_port = dialog.port_combo.currentText()
            baud_rate = dialog.baud_combo.currentText()
            print(f"Config: {config_name}, Port: {com_port}, Baud: {baud_rate}")

    def open_printer_config_dialog(self):
        """Открыть диалог настроек термопринтера"""
        dialog = ThermalPrinterDialog(parent=self, printer_manager=self.printer_manager)
        dialog.exec_()

    def open_user_management_dialog(self):
        """Открыть диалог управления пользователями"""
        if self.current_user != "admin":
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Только администратор может управлять пользователями.")
            return
        dialog = UserManagementDialog(parent=self)
        dialog.exec_()

    def on_delete_record(self):
        """Удалить выбранную запись из таблицы"""
        if self.current_user != "admin":
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Только администратор может удалять записи.")
            return

        table = self.left_panel.table

        # Получить индексы выделенных строк
        selected_rows = table.selectionModel().selectedRows() if table.selectionModel() else []
        if not selected_rows:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления.")
            return

        # Подтверждение удаления
        count = len(selected_rows)
        message = f"Вы действительно хотите удалить {count} запись(ей)?" if count > 1 else "Вы действительно хотите удалить выбранную запись?"
        reply = QtWidgets.QMessageBox.question(
            self,
            'Подтверждение удаления',
            message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Получить данные для удаления из базы
            import sqlite3
            conn = sqlite3.connect('weights_journal.db')
            cursor = conn.cursor()

            deleted_count = 0
            for index in sorted(selected_rows, reverse=True):
                row = index.row()
                # Получить данные из таблицы для идентификации записи
                datetime_val = table.item(row, 0).text() if table.item(row, 0) else ""
                weight_val = table.item(row, 1).text() if table.item(row, 1) else ""
                operator_val = table.item(row, 3).text() if table.item(row, 3) else ""

                # Удалить из базы данных
                cursor.execute('''
                    DELETE FROM weighings
                    WHERE datetime=? AND weight=? AND operator=?
                ''', (datetime_val, float(weight_val.replace(' кг', '').replace(',', '.')) if weight_val else 0, operator_val))

                deleted_count += cursor.rowcount
                # Удалить из таблицы
                table.removeRow(row)

            conn.commit()
            conn.close()

            QtWidgets.QMessageBox.information(self, "Успех", f"Удалено {deleted_count} запись(ей).")
            # Обновить сводку
            self.left_panel.on_selection_changed()

    def open_login_dialog(self):
        dialog = LoginDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            username = dialog.logged_in_user
            self.current_user = username
            self.header.set_logged_in_user(username)
            # ВАЖНО: здесь обновляем текущего пользователя scales_manager и загружаем конфигурации
            self.scales_manager.set_current_user(username)
            # Обновляем левую панель для показа таблицы пользователя
            self.left_panel.set_current_user(username)
            # Обновляем футер
            self.footer.set_user(username)
            QtWidgets.QMessageBox.information(self, "Успех", f"Пользователь '{username}' успешно авторизован.")

    def on_logout(self):
        # Запрашиваем подтверждение перед выходом
        reply = QtWidgets.QMessageBox.question(
            self,
            'Подтверждение выхода',
            'Вы действительно хотите выйти из системы?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Выполняем выход из системы
            self.current_user = None
            self.header.logout()
            self.scales_manager.set_current_user(None)  # Очистить пользователя после выхода
            # Обновляем левую панель для показа сообщения о необходимости входа
            self.left_panel.set_current_user(None)
            # Обновляем футер
            self.footer.set_user(None)
            QtWidgets.QMessageBox.information(self, "Сеанс завершён", "Вы вышли из системы.")

    def closeEvent(self, a0):
        """Обработчик события закрытия окна с подтверждением"""
        reply = QtWidgets.QMessageBox.question(
            self,
            'Подтверждение выхода',
            'Вы действительно хотите выйти из приложения?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            a0.accept()  # Закрываем приложение
        else:
            a0.ignore()  # Игнорируем событие закрытия


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = WeighingJournal()
    window.show()
    sys.exit(app.exec_())
