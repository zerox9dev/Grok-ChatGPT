from typing import Dict, List

from openai import AsyncOpenAI

from config import GPT_MODEL, MAX_TOKENS, OPENAI_API_KEY


class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    async def get_response(
        self, message: str, context: List[Dict[str, str]] = None
    ) -> str:
        try:
            if context is None:
                context = []
            messages = context + [{"role": "user", "content": message}]
            response = await self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при получении ответа: {str(e)}"

    async def generate_image(self, prompt: str) -> str:
        try:
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="hd",
                n=1,
            )
            return response.data[0].url
        except Exception as e:
            raise Exception(f"Ошибка генерации изображения: {str(e)}")
