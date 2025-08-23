# AIHelper Bot

![AIHelper Bot Overview](image/overview.jpg)

A Telegram bot providing direct access to modern AI models (GPT, Claude) through your messenger. Simple, efficient, and user-friendly.

## Features

- **Multiple AI Models**: GPT and Claude support via official APIs
- **Smart Conversations**: Context memory and image analysis
- **Token Economy**: Daily free tokens and referral system  
- **Multi-language**: Russian, English, Ukrainian interfaces
- **Admin Tools**: Monitoring and management panel

## Installation

1. **Clone repository**
```bash
git clone https://github.com/zerox9dev/Grok-ChatGPT
cd aihelper-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
Create `.env` file with your API keys (see example below)

4. **Run the bot**
```bash
python main.py
```

## Environment Variables

```env
# Model settings
GPT_MODEL=gpt-5
CLAUDE_MODEL=claude-3-7-sonnet-20250219

# API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Telegram and MongoDB
BOT_TOKEN=your_telegram_bot_token
MONGO_URL=your_mongodb_url
```

## Bot Commands

- `/start` - Initialize the bot
- `/models` - Select AI model (GPT/Claude)  
- `/invite` - Get referral link
- `/profile` - View profile and token balance
- `/reset` - Clear conversation history
- `/help` - Get usage help

## Tech Stack

- **aiogram 3.x** - Telegram Bot API framework
- **MongoDB** (motor) - Async database operations
- **OpenAI API** - GPT models integration
- **Anthropic API** - Claude models integration
- **APScheduler** - Scheduled tasks (daily tokens)

## Project Structure

```
aihelper-bot/
├── bot/
│   ├── database/        # MongoDB operations
│   ├── handlers/        # Command handlers  
│   ├── keyboards/       # Bot keyboards
│   ├── locales/         # Multi-language support
│   ├── services/        # AI services integration
│   └── utils/           # Helper functions
├── config.py            # Configuration
├── main.py              # Entry point
└── requirements.txt     # Dependencies
```

## License

MIT

## Contact

Questions or suggestions? Contact me via [Telegram](https://t.me/zerox9dev).