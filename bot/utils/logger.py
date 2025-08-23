import logging

# ================================================
# Конфигурация логирования
# ================================================
def setup_logger(name: str = __name__) -> logging.Logger:
    """Настройка логгера с единым форматом для всех модулей проекта"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Настройка формата логов с эмодзи для удобства
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Обработчик для консоли
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Добавляем обработчик к логгеру
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
        
        # Отключаем дублирование логов в родительских логгерах
        logger.propagate = False
    
    return logger

# ================================================
# Базовый логгер для всего проекта
# ================================================
logger = setup_logger('telegram_bot')
