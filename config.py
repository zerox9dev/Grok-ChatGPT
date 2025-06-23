# Импорт библиотек
from environs import (
    Env,
)  # Импорт класса Env из библиотеки environs для работы с переменными окружения

# Инициализация окружения
env = Env()  # Создание объекта Env для управления переменными окружения
env.read_env()  # Чтение переменных из файла .env


YOUR_ADMIN_ID = 1483953251

# Конфигурация моделей искусственного интеллекта
GPT_MODEL = env.str("GPT_MODEL")  # Название или идентификатор модели GPT
CLAUDE_MODEL = env.str("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")  # Название или идентификатор модели Claude

# Настройки реферальной системы
REFERRAL_TOKENS = (
    10  # Количество токенов, начисляемых за приглашение по реферальной ссылке
)
REQUIRED_CHANNELS = [
    "@Pix2Code",  # Первый обязательный канал
    "@talentx_tg"  # Второй обязательный канал - замените на нужное имя
]

# API-ключи для сервисов ИИ
OPENAI_API_KEY = env.str("OPENAI_API_KEY")  # Ключ API для доступа к OpenAI
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY")  # Ключ API для доступа к Anthropic

MODEL_NAMES = {
    GPT_MODEL: "GPT o3",
    CLAUDE_MODEL: "Claude 4",
}

# Конфигурация бота и базы данных
BOT_TOKEN = env.str("BOT_TOKEN")  # Токен для авторизации Telegram-бота
MONGO_URL = env.str("MONGO_URL")  # URL-адрес для подключения к базе данных MongoDB

# Настройки веб-сервера
WEB_SERVER_HOST = "0.0.0.0"  # Хост веб-сервера, доступный для всех сетевых интерфейсов
PORT = env.int("PORT")  # Порт для запуска веб-сервера, задается в переменной окружения
WEBHOOK_PATH = "/telegram-webhook"  # Путь для обработки входящих запросов от Telegram
WEBHOOK_URL = env.str("WEBHOOK_URL")  # Полный URL-адрес вебхука для Telegram

# Тарифы и токены
FREE_TOKENS = 10  # Количество токенов, предоставляемых бесплатно новым пользователям
DAILY_TOKENS = 10  # Ежедневное начисление токенов для пользователей с платным тарифом
PAID_TARIFF_PRICE = 5  # Стоимость подключения платного тарифа (в условных единицах)
MAX_TOKENS = 1000  # Максимально допустимое количество токенов для одного запроса
