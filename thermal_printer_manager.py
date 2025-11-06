import serial
import serial.tools.list_ports


class ThermalPrinterManager:
    def __init__(self):
        self.serial_connection = None
        self.is_connected = False
        self.port = None
        self.baud_rate = 9600

    def get_available_ports(self):
        """Получить список доступных COM портов"""
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port, baud_rate=9600):
        """Подключиться к принтеру"""
        if self.is_connected:
            self.disconnect()

        try:
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            self.is_connected = True
            self.port = port
            self.baud_rate = baud_rate
            self.initialize_printer_for_cyrillic()
            return True, f"Подключено к {port}"
        except Exception as e:
            return False, f"Ошибка подключения: {str(e)}"

    def disconnect(self):
        """Отключиться от принтера"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_connected = False
        self.port = None

    def print_receipt(self, receipt_data):
        """Распечатать чек с данными"""
        if not self.is_connected:
            return False, "Принтер не подключен"

        try:
            if not self.serial_connection or not self.serial_connection.is_open:
                return False, "Соединение с принтером потеряно"

            # Форматируем данные чека
            receipt_text = self.format_receipt_text(receipt_data)

            # Кодируем текст в GB18030
            encoded_text = receipt_text.encode('gb18030', errors='replace')
            self.serial_connection.write(encoded_text)

            # Отправляем перевод строки для фида бумаги
            self.serial_connection.write(b'\n\n')  # Двойной перевод для отрыва

            return True, "Чек распечатан успешно"

        except Exception as e:
            return False, f"Ошибка печати: {str(e)}"

    def format_receipt_text(self, data):
        """Форматировать текст чека"""
        lines = []

        # Заголовок чека
        lines.append(" " * 8 + "ТОВАРНЫЙ ЧЕК")
        lines.append("-" * 30)

        # Название организации
        lines.append(" " * 8 + "ВЕС-СЕРВИС")
        lines.append("")

        # Дата и время
        if 'datetime' in data and data['datetime']:
            lines.append(f"Дата/Время: {data['datetime']}")
        lines.append("")

        # Наименование товара
        if 'name' in data and data['name'] and data['name'] != '-':
            lines.append(f"Наименование товара: {data['name']}")
        else:
            lines.append("Наименование товара: Весовой товар")
        lines.append("")

        # Вес в кг
        if 'weight' in data and data['weight']:
            lines.append(f"Масса нетто: {data['weight']} кг")
        else:
            lines.append("Масса нетто: - кг")
        lines.append("")

        # Отправитель
        if 'sender' in data and data['sender'] and data['sender'] != '-':
            lines.append(f"Отправитель: {data['sender']}")
        lines.append("")

        # Получатель
        if 'receiver' in data and data['receiver'] and data['receiver'] != '-':
            lines.append(f"Получатель: {data['receiver']}")
        lines.append("")

        # Оператор
        if 'operator' in data and data['operator']:
            lines.append(f"Оператор: {data['operator']}")
        lines.append("")

        # Примечание
        if 'notes' in data and data['notes'] and data['notes'] != '-':
            lines.append(f"Примечание: {data['notes']}")
        lines.append("")

        # Итого
        lines.append("-" * 30)
        lines.append("ИТОГО: ------- руб.")
        lines.append("")

        # Подпись
        lines.append(" " * 15 + "____________")
        lines.append("")

        # Нижний разделитель
        lines.append("=" * 30)
        lines.append(" " * 8 + "СПАСИБО ЗА ПОКУПКУ!")
        lines.append("")

        return "\n".join(lines)

    def initialize_printer_for_cyrillic(self):
        """Инициализировать принтер для печати русского текста"""
        if not self.serial_connection:
            return

        # Шаг 1: Полная инициализация принтера
        self.serial_connection.write(b'\x1B@')        # ESC @ - инициализация

        # Шаг 2: Устанавливаем межсимвольный интервал (уменьшаем расстояние между буквами)
        self.serial_connection.write(b'\x1B\x20\x00')  # ESC SP 0 - межсимвольный интервал 0

        # Шаг 3: Включаем китайский режим для поддержки кириллицы (GB18030)
        self.serial_connection.write(b'\x1C&')        # FS & - включить режим с кириллицей

        # Шаг 4: Настраиваем выравнивание влево
        self.serial_connection.write(b'\x1B\x61\x00')     # ESC a 0 - выравнивание слева