import os

from openai import AsyncOpenAI

from config import GROK_MODEL, MAX_TOKENS, XAI_API_KEY


class GrokService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

    async def get_response(self, message: str) -> str:
        try:
            completion = await self.client.chat.completions.create(
                model=GROK_MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": message}],
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Ошибка при получении ответа от Grok: {str(e)}"
