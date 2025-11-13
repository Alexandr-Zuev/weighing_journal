import re
import time
import serial
from typing import Optional, Union, Tuple


class WeightReader:
    """Класс для чтения данных с COM-порта и парсинга веса"""

    def __init__(self, port: Optional[str] = None, baudrate: int = 9600, protocol: int = 1):
        self.serial_port: Optional[serial.Serial] = None
        self.port = port
        self.baudrate = baudrate
        self.protocol = protocol  # 1: ww005kg, 2: ST,GS,+000005kg
        self.is_connected = False

    def connect(self, port: str, baudrate: int = 9600) -> Tuple[bool, str]:
        """Подключиться к COM-порту"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1
            )
            self.port = port
            self.baudrate = baudrate
            self.is_connected = True
            return True, f"Подключено к {port} с скоростью {baudrate}"
        except Exception as e:
            self.is_connected = False
            return False, f"Ошибка подключения: {str(e)}"

    def disconnect(self):
        """Отключиться от COM-порта"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
        except Exception:
            pass
        finally:
            self.serial_port = None
            self.is_connected = False

    def read_weight(self) -> Optional[float]:
        """Прочитать и распарсить вес с COM-порта"""
        if not self.is_connected or not self.serial_port or not self.serial_port.is_open:
            return None

        try:
            if self.serial_port.in_waiting:
                raw_bytes = self.serial_port.readline()
                if raw_bytes:
                    raw_string = raw_bytes.decode('utf-8').strip()
                    weight_value = self.parse_weight_from_raw(raw_string)
                    if weight_value is not None and isinstance(weight_value, (int, float)) and weight_value >= 0:
                        return weight_value
        except Exception:
            # Игнорируем ошибки чтения
            pass

        return None

    def parse_weight_from_raw(self, raw_string: str) -> Optional[float]:
        """Парсит строку веса в зависимости от текущего протокола.

        Протокол 1: строки вида 'ww005.5kg' или 'ww 005.5 kg' -> число 20.12
        Протокол 2: строки вида 'ST, GS,+000005 kg' -> число 5
        """
        if not raw_string or not raw_string.strip():
            return None

        try:
            if self.protocol == 2:
                # Протокол 2: строки вида 'ST, GS,+000005 kg'
                # Ищем образец с числом и 'kg' в конце, может содержать + и пробелы
                match = re.search(r'[A-Z]{2},\s*GS,\s*[+\-]?\s*(\d+(?:\.\d+)?)\s*kg', raw_string.strip())
                if match:
                    value_str = match.group(1).strip()
                    try:
                        value = float(value_str) if '.' in value_str else int(value_str)
                        return value if value >= 0 else None
                    except ValueError:
                        pass
            else:
                # Протокол 1: строки вида 'ww00020.12kg' или 'ww 00020.12 kg'
                # Ищем ww + любое количество цифр + необязательная десятичная часть + kg
                match = re.search(r'ww\s*(\d+(?:\.\d+)?)\s*kg', raw_string.strip().lower())
                if match:
                    value_str = match.group(1).strip()
                    try:
                        value = float(value_str) if '.' in value_str else int(value_str)
                        return value if value >= 0 else None
                    except ValueError:
                        pass

                # Альтернативный формат без 'kg' но с 'ww'
                alt_match = re.search(r'ww\s*(\d+(?:\.\d+)?)', raw_string.strip().lower())
                if alt_match:
                    value_str = alt_match.group(1).strip()
                    try:
                        value = float(value_str) if '.' in value_str else int(value_str)
                        return value if value >= 0 else None
                    except ValueError:
                        pass

            # Если основные протоколы не сработали, ищем числа с десятичной точкой или запятой
            # Но только если они выглядят как вес (положительные числа)
            number_patterns = [
                r'(\d+(?:[.,]\d+)?)',  # числа с точкой или запятой как разделителем
            ]

            for pattern in number_patterns:
                matches = re.findall(pattern, raw_string.strip())
                for match in matches:
                    # Заменяем запятую на точку для корректного преобразования
                    value_str = match.replace(',', '.')
                    try:
                        value = float(value_str)
                        # Проверяем, что это разумное значение веса (не слишком большое)
                        if 0 <= value <= 100000:  # Разумный предел для веса в кг
                            return value
                    except ValueError:
                        continue

        except Exception:
            # Игнорируем любые ошибки парсинга
            pass

        return None

    def set_protocol(self, protocol: int):
        """Установить протокол обмена данными"""
        self.protocol = protocol

    def is_port_open(self) -> bool:
        """Проверить, открыт ли порт"""
        return self.is_connected and self.serial_port is not None and self.serial_port.is_open