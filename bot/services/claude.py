import base64
from typing import Dict, List

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS


class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    async def get_response(
        self, message: str, context: List[Dict[str, str]] = None, system_prompt: str = None
    ) -> str:
        """
        Получает ответ от модели Claude
        
        Args:
            message: Текст сообщения пользователя
            context: Контекст предыдущей беседы в формате [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            system_prompt: Системный промпт для модели
            
        Returns:
            Текстовый ответ от модели Claude
        """
        try:
            # Подготовка сообщений в правильном формате для Anthropic API
            anthropic_messages = []
            
            # Добавляем контекст, преобразуя формат OpenAI в формат Anthropic
            if context:
                for msg in context:
                    role = msg["role"]
                    content = msg["content"]
                    
                    # Проверяем, что content не является списком (формат контента OpenAI GPT-4 Vision)
                    if isinstance(content, list):
                        # Конвертируем сложную структуру в текст
                        text_content = ""
                        for item in content:
                            if item.get("type") == "text":
                                text_content += item.get("text", "")
                        content = text_content
                    
                    if role == "user":
                        anthropic_messages.append({"role": "user", "content": content})
                    elif role == "assistant":
                        anthropic_messages.append({"role": "assistant", "content": content})
            
            # Добавляем текущее сообщение пользователя
            anthropic_messages.append({"role": "user", "content": message})
            
            # Создаем запрос к Claude API (синхронно)
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=0.7,
                system=system_prompt if system_prompt else "Ты полезный ИИ-ассистент. Отвечай кратко и по существу.",
                messages=anthropic_messages
            )
            
            return response.content[0].text
        except Exception as e:
            return f"Ошибка при получении ответа от Claude: {str(e)}"

    async def read_image(self, image_path: str) -> str:
        """
        Анализирует изображение с помощью Claude
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Текстовое описание изображения
        """
        try:
            # Открываем и кодируем изображение в base64
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                
            # Создаем сообщение с изображением для Claude (синхронно)
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=0.7,
                system="Опиши детально, что изображено на этой фотографии.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64.b64encode(image_data).decode("utf-8")
                                }
                            },
                            {
                                "type": "text",
                                "text": "Опиши подробно это изображение:"
                            }
                        ]
                    }
                ]
            )
            
            return response.content[0].text
        except Exception as e:
            return f"Ошибка при обработке изображения: {str(e)}" 