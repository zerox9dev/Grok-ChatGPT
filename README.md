# AIHelper Bot

My Telegram bot providing access to modern AI models (GPT-4O, Claude 3, Grok) directly in your messenger. Created for convenient work with neural networks without unnecessary complications.

## Features

- **Multiple AI Models**: support for GPT-4O, Claude 3, Grok 2, and DeepSeek V3
- **Content Generation**:
  - Text responses with context memory
  - Image creation through DALL-E 3
  - Text-to-speech conversion
  - Image analysis (send a photo → get a description)
- **Token Economy**:
  - Daily free tokens
  - Referral system: invite friends → get tokens
- **Multilingual**: support for Russian, Ukrainian, and English
- **Convenient Administration**: user management and mass messaging

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/aihelper-bot.git
cd aihelper-bot
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the necessary environment variables

4. Run the bot
```bash
python main.py
```

## Environment Variables

```env
# API Keys for models
OPENAI_API_KEY=sk-your_openai_key
ANTHROPIC_API_KEY=sk-your_anthropic_key
XAI_API_KEY=your_xai_key
TOGETHER_API_KEY=your_together_key

# Model settings
GPT_MODEL=gpt-4o
CLAUDE_MODEL=claude-3-opus-20240229
GROK_MODEL=grok-2
TOGETHER_MODEL=DeepSeek-Coder-V3-Instruct

# Telegram and MongoDB settings
BOT_TOKEN=your_telegram_bot_token
MONGO_URL=your_mongodb_url

# Webhook settings
PORT=8443
WEBHOOK_URL=https://your_domain
```

## Bot Commands

- `/start` - start working with the bot
- `/models` - select AI model
- `/image [prompt]` - generate an image based on prompt
- `/audio [text]` - convert text to speech
- `/invite` - get a referral link
- `/profile` - information about your profile and balance
- `/reset` - reset conversation history (context)
- `/help` - get help on using the bot

## Architecture

The bot is built on a modern technology stack:

- **aiogram 3.x** - for interacting with Telegram API
- **MongoDB** (motor) - asynchronous database operations
- **OpenAI API** - for access to GPT-4O and DALL-E 3
- **Anthropic API** - for working with Claude 3
- **X.AI API** - for integration with Grok
- **Together AI** - for using DeepSeek Coder V3
- **APScheduler** - for executing scheduled tasks

## Project Structure

```
aihelper-bot/
├── bot/
│   ├── database/        # MongoDB operations
│   ├── handlers/        # Command handlers
│   ├── keyboards/       # Bot keyboards
│   ├── locales/         # Multilingual support
│   ├── services/        # AI services integration
│   └── utils/           # Helper functions
├── config.py            # Project configuration
├── main.py              # Main entry file
└── requirements.txt     # Dependencies
```

## License

MIT

## Contact

If you have any questions or suggestions for improving the bot, contact me via [Telegram](https://t.me/mirvaId).