from environs import (
    Env,
)  # Импорт библиотеки environs для работы с переменными окружения

env = Env()  # Создание объекта Env для работы с окружением
env.read_env()  # Чтение переменных из файла .env

# Блок конфигурации моделей искусственного интеллекта
GPT_MODEL = env.str("GPT_MODEL")  # Модель GPT (название или идентификатор)
CLAUDE_MODEL = env.str("CLAUDE_MODEL")  # Модель Claude
TOGETHER_MODEL = env.str("TOGETHER_MODEL")  # Модель Together AI
GROK_MODEL = env.str("GROK_MODEL")  # Модель Grok (xAI)

# Блок API-ключей для доступа к сервисам ИИ
TOGETHER_API_KEY = env.str("TOGETHER_API_KEY")  # API-ключ для Together AI
OPENAI_API_KEY = env.str("OPENAI_API_KEY")  # API-ключ для OpenAI
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY")  # API-ключ для Anthropic
XAI_API_KEY = env.str("XAI_API_KEY")  # API-ключ для xAI

# Основные настройки бота и базы данных
BOT_TOKEN = env.str("BOT_TOKEN")  # Токен Telegram-бота
MONGO_URL = env.str("MONGO_URL")  # URL для подключения к MongoDB

# Настройки веб-сервера
WEB_SERVER_HOST = "0.0.0.0"  # Хост веб-сервера (доступен для всех интерфейсов)
PORT = env.int("PORT")  # Порт для веб-сервера (берется из переменной окружения)
WEBHOOK_PATH = "/telegram-webhook"  # Путь для вебхука Telegram
WEBHOOK_URL = env.str("WEBHOOK_URL")  # Полный URL вебхука

# Настройки генерации изображений
DALLE_MODEL = "dall-e-3"  # Модель DALL-E для генерации изображений
IMAGE_COST = 5  # Стоимость генерации одного изображения в токенах

# Настройки тарифов и токенов
FREE_TOKENS = 10  # Количество бесплатных токенов для новых пользователей
DAILY_TOKENS = 10  # Ежедневное количество токенов для платного тарифа
PAID_TARIFF_PRICE = 5  # Стоимость платного тарифа (в валюте или единицах)
MAX_TOKENS = 1000  # Максимальное количество токенов в запросе
