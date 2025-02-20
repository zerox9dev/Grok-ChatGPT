from together import Together

from config import MAX_TOKENS, TOGETHER_API_KEY, TOGETHER_MODEL


class TogetherService:
    def __init__(self):
        self.client = Together(api_key=TOGETHER_API_KEY)

    async def get_response(self, message: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=TOGETHER_MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": message}],
            )
            return response.choices[0].message.content

        except Exception as e:
            return f"Ошибка при получении ответа от together: {str(e)}"
