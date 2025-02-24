from environs import Env

env = Env()
env.read_env()

# models_ai
GPT_MODEL = env.str("GPT_MODEL")
CLAUDE_MODEL = env.str("CLAUDE_MODEL")
TOGETHER_MODEL = env.str("TOGETHER_MODEL")
GROK_MODEL = env.str("GROK_MODEL")


# AI_KEY
TOGETHER_API_KEY = env.str("TOGETHER_API_KEY")
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY")
XAI_API_KEY = env.str("XAI_API_KEY")

BOT_TOKEN = env.str("BOT_TOKEN")
MONGO_URL = env.str("MONGO_URL")


WEB_SERVER_HOST = "0.0.0.0"
PORT = env.int("PORT")
WEBHOOK_PATH = "/telegram-webhook"
WEBHOOK_URL = env.str("WEBHOOK_URL")


DALLE_MODEL = "dall-e-3"
IMAGE_COST = 5


# Добавьте в начало файла
FREE_TOKENS = 10  # Количество токенов для бесплатного тарифа
DAILY_TOKENS = 10  # Количество токенов для платного тарифа ежедневно
PAID_TARIFF_PRICE = 5  # Стоимость платного тарифа
MAX_TOKENS = 1000
