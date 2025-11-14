import hashlib
import json
import os
import uuid
from datetime import datetime

LICENSE_FILE = 'license.key'

def get_system_uuid():
    """Получает уникальный идентификатор системы"""
    return str(uuid.getnode())

def generate_activation_code():
    """Генерирует код активации на основе MD5 хэша первых 6 символов UUID системы"""
    system_uuid = get_system_uuid()
    first_six = system_uuid[:6]
    hash_object = hashlib.md5(first_six.encode())
    activation_code = hash_object.hexdigest()
    return activation_code

def save_license(activation_code):
    """Сохраняет лицензию в файл license.key"""
    license_data = {
        'activation_code': activation_code,
        'activation_date': datetime.now().isoformat(),
        'system_uuid': get_system_uuid(),
        'status': 'active'
    }
    with open(LICENSE_FILE, 'w', encoding='utf-8') as f:
        json.dump(license_data, f, ensure_ascii=False, indent=2)

def load_license():
    """Загружает лицензию из файла license.key"""
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    return None

def is_license_valid():
    """Проверяет валидность лицензии"""
    license_data = load_license()
    if license_data is None or license_data.get('status') != 'active':
        return False
    expected_code = generate_activation_code()
    return license_data.get('activation_code') == expected_code

def get_license_info():
    """Возвращает информацию о лицензии"""
    license_data = load_license()
    if license_data and is_license_valid():
        return {
            'activation_code': license_data.get('activation_code'),
            'activation_date': license_data.get('activation_date'),
            'system_uuid': license_data.get('system_uuid'),
            'status': license_data.get('status')
        }
    return None

def activate_license(activation_code):
    """Активирует лицензию, если код правильный"""
    expected_code = generate_activation_code()
    if activation_code == expected_code:
        save_license(activation_code)
        return True
    return False