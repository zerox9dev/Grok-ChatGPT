import base64
import os
from typing import Dict, List

from openai import AsyncOpenAI

from config import GROK_MODEL, MAX_TOKENS, XAI_API_KEY


class GrokService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

    async def get_response(
        self, message: str, context: List[Dict[str, str]] = None
    ) -> str:
        try:
            if context is None:
                context = []
            messages = context + [{"role": "user", "content": message}]
            completion = await self.client.chat.completions.create(
                model=GROK_MODEL,
                max_tokens=MAX_TOKENS,
                messages=messages,
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"An error occurred while receiving a reply from Grok: {str(e)}"

    async def generate_image(self, prompt: str, n: int = 1) -> str:
        """
        Генерирует изображение с помощью Grok API
        """
        try:
            response = await self.client.images.generate(
                model="grok-2-image",
                prompt=prompt,
                response_format="url",
                n=n,
            )
            return response.data[0].url
        except Exception as e:
            raise Exception(f"Ошибка генерации изображения Grok: {str(e)}")

    async def read_image(self, image_path: str) -> str:
        try:

            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

            response = await self.client.chat.completions.create(
                model="grok-vision-beta",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Опиши это изображение:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=MAX_TOKENS,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при обработке изображения: {str(e)}"
