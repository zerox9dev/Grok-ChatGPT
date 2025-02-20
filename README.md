# AI Guide Bot

Telegram bot with multiple AI models (GPT-4O, Claude 3) integration and Stripe payments.

## Features

- Multiple AI models support (GPT-4O, Claude 3)
- Token-based payment system
- Stripe integration
- MongoDB database
- Webhook support

## Installation

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env`
4. Run bot: `python main.py`

## Environment Variables

```env
BOT_TOKEN=your_telegram_bot_token
MONGO_URL=your_mongodb_url
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
STRIPE_API_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```
