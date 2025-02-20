from openai import AsyncOpenAI

from config import OPENAI_API_KEY


class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    async def get_response(self, message: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": message}],
                max_tokens=1000,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при получении ответа: {str(e)}"
