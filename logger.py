import logging
import os
from datetime import datetime

# Создаем директорию для логов если её нет
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f"weighing_journal_{datetime.now().strftime('%Y%m%d')}.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Создаем логгер для приложения
logger = logging.getLogger('weighing_journal')

# Функция для получения логгера с именем модуля
def get_logger(name):
    return logging.getLogger(f'weighing_journal.{name}')