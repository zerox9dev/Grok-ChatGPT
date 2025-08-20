# Импорт библиотек
from environs import (
    Env,
)  # Импорт класса Env из библиотеки environs для работы с переменными окружения

# Инициализация окружения
env = Env()  # Создание объекта Env для управления переменными окружения
env.read_env()  # Чтение переменных из файла .env


YOUR_ADMIN_ID = 1483953251

# Конфигурация моделей искусственного интеллекта
GPT_MODEL = env.str("GPT_MODEL", "gpt-5")  # Название или идентификатор модели GPT
CLAUDE_MODEL = env.str("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")  # Название или идентификатор модели Claude

# Конфигурация API ключей
OPENAI_API_KEY = env.str("OPENAI_API_KEY")  # API ключ для OpenAI
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY", None)  # API ключ для Anthropic (опционально)

# Настройки реферальной системы
REFERRAL_TOKENS = (
    10  # Количество токенов, начисляемых за приглашение по реферальной ссылке
)




# Конфигурация бота и базы данных
BOT_TOKEN = env.str("BOT_TOKEN")  # Токен для авторизации Telegram-бота
MONGO_URL = env.str("MONGO_URL")  # URL-адрес для подключения к базе данных MongoDB



# Тарифы и токены
FREE_TOKENS = 10  # Количество токенов, предоставляемых бесплатно новым пользователям
DAILY_TOKENS = 10  # Ежедневное начисление токенов для пользователей с платным тарифом
