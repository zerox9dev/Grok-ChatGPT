from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN")
MONGO_URL = env.str("MONGO_URL")
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY")
STRIPE_API_KEY = env.str("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = env.str("STRIPE_WEBHOOK_SECRET")
