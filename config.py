from environs import Env

env = Env()
env.read_env()

# models_ai
GPT_MODEL = env.str("GPT_MODEL")
CLAUDE_MODEL = env.str("CLAUDE_MODEL")

# Settings
MAX_TOKENS = 1000

BOT_TOKEN = env.str("BOT_TOKEN")
MONGO_URL = env.str("MONGO_URL")
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY")
STRIPE_API_KEY = env.str("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = env.str("STRIPE_WEBHOOK_SECRET")
