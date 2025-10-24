import sqlite3
from PyQt5 import QtWidgets, QtCore, QtGui
from right_panel import RightPanelWidget

DB_FILE = 'weights_journal.db'

class ScalesManager(QtWidgets.QWidget):
    """Менеджер для управления несколькими блоками весов"""

    # Сигнал для уведомления о новом взвешивании
    weighing_saved = QtCore.pyqtSignal()

    def __init__(self, font_family="Arial", parent=None):
        super().__init__(parent)
        self.font_family = font_family
        self.current_user = None
        self.scales_widgets = []  # Список всех виджетов весов
        self.scales_counter = 1   # Счетчик для нумерации весов

        # Создаем scroll area для возможности прокрутки при множестве весов
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        # Контейнер для весов внутри scroll area
        self.container = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.container)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(15)

        self.scroll_area.setWidget(self.container)

        # Основной layout для всего виджета
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll_area)

        # Добавляем первую весы по умолчанию
        self.add_scales()

    def add_scales(self):
        """Добавляет новый блок весов"""
        scales_number = self.scales_counter
        self.scales_counter += 1

        # Создаем новый виджет весов (показываем информационный блок только для первой весы)
        show_info_block = (scales_number == 1)
        scales_widget = RightPanelWidget(
            font_family=self.font_family,
            parent=self,
            current_user=self.current_user,
            scales_number=scales_number,
            show_info_block=show_info_block
        )

        # Подключаем сигналы
        scales_widget.weighing_saved.connect(self.weighing_saved.emit)
        scales_widget.delete_requested.connect(lambda: self.remove_scales(scales_widget))

        # Добавляем в список и layout
        self.scales_widgets.append(scales_widget)
        self.layout.addWidget(scales_widget)

        # Добавляем растягивающийся элемент в конец, чтобы весы не растягивались
        if len(self.scales_widgets) == 1:
            self.layout.addStretch()

        return scales_widget

    def _update_scales_title(self, scales_widget, number):
        """Обновляет заголовок блока весов"""
        # Ищем QLabel с заголовком в виджете весов
        def find_title_label(widget):
            for child in widget.findChildren(QtWidgets.QLabel):
                if "Весы№" in child.text():
                    return child
            return None

        title_label = find_title_label(scales_widget)
        if title_label:
            title_label.setText(f"Весы№{number}")

    def remove_scales(self, scales_widget):
        """Удаляет блок весов"""
        if scales_widget in self.scales_widgets:
            # Не разрешаем удалять первую весы
            if len(self.scales_widgets) == 1:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Нельзя удалить единственную весы. Добавьте новую весы перед удалением этой."
                )
                return

            # Получаем номер весов для отображения в сообщении
            def find_scales_number(widget):
                for child in widget.findChildren(QtWidgets.QLabel):
                    text = child.text()
                    if text.startswith("Весы№"):
                        return text
                return "Неизвестная весы"

            scales_number = find_scales_number(scales_widget)

            # Запрашиваем подтверждение перед удалением
            reply = QtWidgets.QMessageBox.question(
                self,
                'Подтверждение удаления',
                f'Вы действительно хотите удалить {scales_number}?\n\nЭто действие нельзя отменить.',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply != QtWidgets.QMessageBox.Yes:
                return  # Пользователь отменил удаление

            # Отключаем сигналы перед удалением
            scales_widget.weighing_saved.disconnect()
            scales_widget.delete_requested.disconnect()

            # Удаляем из списка и layout
            self.scales_widgets.remove(scales_widget)
            self.layout.removeWidget(scales_widget)
            scales_widget.deleteLater()

            # Обновляем нумерацию оставшихся весов
            self._update_scales_numbers()

            # Уменьшаем счетчик, если удаляем последнюю весы
            if self.scales_counter > len(self.scales_widgets) + 1:
                self.scales_counter = len(self.scales_widgets) + 1

    def _update_scales_numbers(self):
        """Обновляет номера всех весов после удаления"""
        for i, scales_widget in enumerate(self.scales_widgets, 1):
            # Обновляем заголовок весов
            def find_title_label(widget):
                for child in widget.findChildren(QtWidgets.QLabel):
                    text = child.text()
                    if text.startswith("Весы№"):
                        return child
                return None

            title_label = find_title_label(scales_widget)
            if title_label:
                title_label.setText(f"Весы№{i}")

            # Обновляем параметр show_info_block (только первая весы показывает информационный блок)
            old_show_info = scales_widget.show_info_block
            scales_widget.show_info_block = (i == 1)

            # Если параметр изменился, обновляем видимость блока информации
            if old_show_info != scales_widget.show_info_block:
                scales_widget.update_info_block_visibility()

    def set_current_user(self, user):
        """Устанавливает текущего пользователя для всех весов"""
        self.current_user = user
        for scales_widget in self.scales_widgets:
            scales_widget.current_user = user
            scales_widget.load_configurations_into_combo()

    def get_scales_count(self):
        """Возвращает количество весов"""
        return len(self.scales_widgets)

    def get_scales_widgets(self):
        """Возвращает список всех виджетов весов"""
        return self.scales_widgets.copy()