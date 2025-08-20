from environs import Env

# ================================================
# Инициализация конфигурации
# ================================================
env = Env()
env.read_env()

# ================================================
# Основные настройки
# ================================================
YOUR_ADMIN_ID = 1483953251

# Модели ИИ
GPT_MODEL = env.str("GPT_MODEL", "gpt-5")
CLAUDE_MODEL = env.str("CLAUDE_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = env.int("MAX_TOKENS", 1000)

# API ключи
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY", None)

# Бот и база данных
BOT_TOKEN = env.str("BOT_TOKEN")
MONGO_URL = env.str("MONGO_URL")

# Токены и тарифы
FREE_TOKENS = 10
DAILY_TOKENS = 10
REFERRAL_TOKENS = 10
