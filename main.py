import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import QtPrintSupport
from header import HeaderWidget
from left_panel import LeftPanelWidget
from scales_manager import ScalesManager
from footer import FooterWidget
from com_config_dialog import ComConfigDialog
from login_dialog import LoginDialog
import csv


class WeighingJournal(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Журнал взвешиваний")
        self.resize(1300, 820)

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
        h_layout.addWidget(self.left_panel, stretch=3)

        self.scales_manager = ScalesManager(font_family=font_family)
        h_layout.addWidget(self.scales_manager, stretch=1)

        self.footer = FooterWidget()
        main_layout.addWidget(self.footer)

        self.current_user = None

        # Подключение сигналов из HeaderWidget
        self.header.system_clicked.connect(self.open_com_config_dialog)
        self.header.login_clicked.connect(self.open_login_dialog)
        self.header.logout_clicked.connect(self.on_logout)
        self.header.add_scales_clicked.connect(self.add_new_scales)
        
        # Подключение сигнала сохранения взвешивания к обновлению таблицы
        self.scales_manager.weighing_saved.connect(self.left_panel.refresh_weighings_data)

        # Связываем сводку и пользователя с футером
        self.left_panel.summary_changed.connect(self.footer.set_status_text)
        self.footer.set_user(self.current_user)

        # Действия футера
        self.footer.print_clicked.connect(self.on_footer_print)
        self.footer.export_clicked.connect(self.on_footer_export)
        self.footer.report_clicked.connect(self.on_footer_report)

    def add_new_scales(self):
        """Добавляет новые весы в интерфейс"""
        self.scales_manager.add_scales()

    def on_footer_print(self):
        # Формирование накладной (PDF)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Сохранить накладную", "nakladnaya.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'

        printer = QtPrintSupport.QPrinter()
        printer.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QtPrintSupport.QPrinter.A4)
        printer.setPageMargins(10, 10, 10, 10, QtPrintSupport.QPrinter.Millimeter)

        painter = QtGui.QPainter(printer)
        try:
            self._draw_invoice(painter, printer)
        finally:
            painter.end()
        QtWidgets.QMessageBox.information(self, "PDF сохранен", f"Файл сохранен: {path}")

    def _draw_invoice(self, painter: QtGui.QPainter, printer: QtPrintSupport.QPrinter):
        # Геометрия страницы
        rect = printer.pageRect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

        # Шрифты
        font_title = QtGui.QFont("Arial", 14, QtGui.QFont.Bold)
        font_small = QtGui.QFont("Arial", 9)
        font_table = QtGui.QFont("Arial", 9)

        # Заголовок
        painter.setFont(font_title)
        title = "НАКЛАДНАЯ № ____________"
        painter.drawText(x, y + 30, w, 30, QtCore.Qt.AlignCenter, title)

        painter.setFont(font_small)
        date_str = QtCore.QDate.currentDate().toString("dd.MM.yyyy")
        painter.drawText(x, y + 60, w, 20, QtCore.Qt.AlignRight, date_str)

        # Поля отправитель/получатель
        topY = y + 90
        line_h = 18
        painter.drawText(x, topY, 120, line_h, QtCore.Qt.AlignLeft, "Отправитель:")
        painter.drawLine(x + 100, topY + line_h - 4, x + w - 20, topY + line_h - 4)
        painter.drawText(x, topY + line_h + 8, 120, line_h, QtCore.Qt.AlignLeft, "Получатель:")
        painter.drawLine(x + 100, topY + 2*line_h + 4, x + w - 20, topY + 2*line_h + 4)

        # Таблица
        startY = topY + 2*line_h + 20
        table_h = h - startY - 40

        headers = [
            "№",
            "Дата/Время",
            "Наименование",
            "Кол-во (кг)",
            "Склад",
            "Отпр.",
            "Получ.",
            "Опер.",
            "Режим",
            "Примечание",
        ]

        # Пропорции колонок (сумма 1.0)
        ratios = [0.05, 0.13, 0.17, 0.1, 0.07, 0.08, 0.08, 0.07, 0.07, 0.18]
        col_x = [x]
        for r in ratios:
            col_x.append(col_x[-1] + int(w * r))

        # Нарисовать шапку
        painter.setFont(font_table)
        header_y = startY
        row_h = 22
        painter.drawRect(x, header_y, w, row_h)
        for i in range(1, len(col_x)):
            painter.drawLine(col_x[i], header_y, col_x[i], header_y + row_h)
        for i, htext in enumerate(headers):
            painter.drawText(col_x[i] + 4, header_y, int(w * ratios[i]) - 8, row_h,
                             QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, htext)

        # Данные из таблицы левой панели — печатаем ТОЛЬКО одну выделенную строку
        table = self.left_panel.table
        y_cursor = header_y + row_h

        # Определяем индекс строки: при наличии выделения берем первую выделенную строку,
        # иначе используем текущую строку, если нет — 0
        selected_rows = table.selectionModel().selectedRows() if table.selectionModel() else []
        if selected_rows:
            row_indices = [selected_rows[0].row()]
        else:
            current = table.currentRow()
            row_indices = [current if current >= 0 else 0]

        for r in row_indices:
            painter.drawRect(x, y_cursor, w, row_h)
            for i in range(1, len(col_x)):
                painter.drawLine(col_x[i], y_cursor, col_x[i], y_cursor + row_h)

            # Сбор данных полей
            idx = r
            def val(ci):
                item = table.item(idx, ci)
                return item.text() if item else ""

            num = str(r + 1)
            datetime_v = val(0)
            weight_v = val(1)
            oper_v = val(2)
            mode_v = val(3)
            name_v = val(4)
            sklad_v = val(5)
            send_v = val(6)
            recv_v = val(7)
            note_v = val(8)

            values = [num, datetime_v, name_v, weight_v, sklad_v, send_v, recv_v, oper_v, mode_v, note_v]
            for i, text in enumerate(values):
                painter.drawText(col_x[i] + 4, y_cursor, int(w * ratios[i]) - 8, row_h,
                                 QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text)
            y_cursor += row_h

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
