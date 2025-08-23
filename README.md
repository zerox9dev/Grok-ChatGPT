# AIHelper Bot

![AIHelper Bot Overview](image/overview.jpg)

A Telegram bot providing direct access to modern AI models (GPT, Claude) through your messenger. Simple, efficient, and user-friendly.

## Features

- **Multiple AI Models**: GPT-5 and Claude 4 Sonnet support via official APIs
- **Custom AI Agents**: Create personalized agents with custom system prompts
- **Smart Conversations**: Context memory (last 5 messages) and image analysis
- **Token Economy**: Daily free tokens (10 requests) and referral system  
- **Multi-language**: Russian, English, Ukrainian interfaces
- **Admin Tools**: Broadcast messages and user management

## Installation

1. **Clone repository**
```bash
git clone https://github.com/zerox9dev/Grok-ChatGPT
cd Grok-ChatGPT
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

- `/start` - Initialize the bot and get welcome message
- `/models` - Select AI model (GPT/Claude)  
- `/agents` - Create and manage custom AI agents with system prompts
- `/invite` - Get referral link to earn tokens
- `/profile` - View profile, token balance, and current mode
- `/reset` - Clear conversation history (context)
- `/help` - Get usage help and information
- `/cancel` - Cancel current agent creation/editing operation

## Tech Stack

- **aiogram 3.x** - Telegram Bot API framework
- **MongoDB** (motor) - Async database operations
- **OpenAI API** - GPT models integration
- **Anthropic API** - Claude models integration
- **APScheduler** - Scheduled tasks (daily tokens)

## Project Structure

```
Grok-ChatGPT/
├── bot/
│   ├── database/        # MongoDB operations and models
│   ├── handlers/        # Command and message handlers  
│   ├── keyboards/       # Inline keyboards
│   ├── locales/         # Multi-language support
│   ├── services/        # AI services (OpenAI, Anthropic)
│   └── utils/           # Daily tokens and helper functions
├── config.py            # Environment configuration
├── main.py              # Bot entry point
├── requirements.txt     # Python dependencies
└── image/               # Bot images and assets
```

## License

MIT

## Contact

Questions or suggestions? Contact me via [Telegram](https://t.me/zerox9dev).