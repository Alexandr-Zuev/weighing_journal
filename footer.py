from PyQt5 import QtWidgets, QtCore


class FooterWidget(QtWidgets.QWidget):
    print_clicked = QtCore.pyqtSignal()
    export_clicked = QtCore.pyqtSignal()
    report_clicked = QtCore.pyqtSignal()
    receipt_print_clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            background: transparent;
            border: none;
            padding: 8px 16px;
            font-size: 10pt;
            color: #111827;
        """)

        footer_layout = QtWidgets.QHBoxLayout(self)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        self.left_footer_label = QtWidgets.QLabel(
            "Отображаются записи: 0 из 0, выбрано: 0"
        )
        self.left_footer_label.setStyleSheet("color: #4b5563; background: transparent;")
        footer_layout.addWidget(self.left_footer_label, alignment=QtCore.Qt.AlignLeft)

        center_widget = QtWidgets.QWidget()
        center_layout = QtWidgets.QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        center_widget.setStyleSheet("background: transparent; border: none;")
        buttons_text = [
            "ПЕЧАТЬ",
            "ЧЕКОПЕЧАТЬ",
            "ЭКСПОРТИРОВАТЬ ДАННЫЕ",
            "ПОДГОТОВИТЬ ОТЧЕТ",
        ]
        btn_style = (
            "QPushButton {"
            "  font-size: 9pt; padding: 4px 12px;"
            "  background: #ffffff; color: #111827;"
            "  border: 1px solid #9ca3af; border-radius: 6px;"
            "}"
            "QPushButton:hover {"
            "  background: #f3f4f6; border-color: #6b7280;"
            "}"
            "QPushButton:pressed {"
            "  background: #e5e7eb; border-color: #6b7280;"
            "}"
            "QPushButton:disabled {"
            "  background: #f9fafb; color: #9ca3af; border-color: #d1d5db;"
            "}"
            "QPushButton:focus {"
            "  outline: none; box-shadow: 0 0 0 2px rgba(59,130,246,0.25);"
            "}"
        )
        self.btn_print = QtWidgets.QPushButton(buttons_text[0])
        self.btn_print.setStyleSheet(btn_style)
        self.btn_receipt_print = QtWidgets.QPushButton(buttons_text[1])
        self.btn_receipt_print.setStyleSheet(btn_style)
        self.btn_export = QtWidgets.QPushButton(buttons_text[2])
        self.btn_export.setStyleSheet(btn_style)
        self.btn_report = QtWidgets.QPushButton(buttons_text[3])
        self.btn_report.setStyleSheet(btn_style)
        center_layout.addWidget(self.btn_print)
        center_layout.addWidget(self.btn_receipt_print)
        center_layout.addWidget(self.btn_export)
        center_layout.addWidget(self.btn_report)
        footer_layout.addWidget(center_widget, alignment=QtCore.Qt.AlignHCenter)

        self.right_footer_label = QtWidgets.QLabel("Пользователь: -")
        self.right_footer_label.setStyleSheet("color: #4b5563; background: transparent;")
        footer_layout.addWidget(self.right_footer_label, alignment=QtCore.Qt.AlignRight)

        # Подключаем сигналы кнопок
        self.btn_print.clicked.connect(self.print_clicked.emit)
        self.btn_receipt_print.clicked.connect(self.receipt_print_clicked.emit)
        self.btn_export.clicked.connect(self.export_clicked.emit)
        self.btn_report.clicked.connect(self.report_clicked.emit)

    def set_status_text(self, text: str):
        self.left_footer_label.setText(text)

    def set_user(self, username: str | None):
        user_display = username if username else "-"
        self.right_footer_label.setText(f"Пользователь: {user_display}")
