from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY


class ClaudeService:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    async def get_response(self, message: str) -> str:
        try:
            response = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": message}],
            )
            return response.content[0].text
        except Exception as e:
            return f"Ошибка при получении ответа от Claude: {str(e)}"
