import base64
from typing import Dict, List, Optional

from g4f.client import Client 

from config import MAX_TOKENS, HUGGINGFACE_API_KEY


class AIService:
    def __init__(self, model_name: str = None):
        """
        Инициализирует сервис для работы с моделями ИИ через g4f
        
        Args:
            model_name: Название модели (если None, будет использоваться gpt-4o-mini)
        """
        self.model_name = model_name or "gpt-4o-mini"
        
        # Инициализируем g4f клиент для всех моделей
        self.client = Client()
    
    def is_claude_model(self) -> bool:
        """Проверяет, является ли текущая модель Claude"""
        return self.model_name and "claude" in self.model_name.lower()
    
    async def get_response(
        self, message: str, context: List[Dict[str, str]] = None, system_prompt: str = None
    ) -> str:
        """
        Получает ответ от выбранной модели ИИ через g4f
        
        Args:
            message: Текст сообщения пользователя
            context: Контекст предыдущей беседы
            system_prompt: Системный промпт для модели
            
        Returns:
            Текстовый ответ от модели
        """
        try:
            if context is None:
                context = []
                
            messages = context + [{"role": "user", "content": message}]
            
            # Добавляем системный промпт, если он есть
            params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": MAX_TOKENS,
                "web_search": False,
            }
            
            # Добавляем системный промпт для моделей, которые его поддерживают
            if system_prompt:
                params["system"] = system_prompt
                
            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при получении ответа: {str(e)}"
    
    async def read_image(self, image_path: str) -> str:
        """
        Анализирует изображение с помощью выбранной модели через g4f
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Текстовое описание изображения
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": [{
                        "type": "text", 
                        "text": "Опиши это изображение:"
                    }, {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
                    }]
                }],
                max_tokens=MAX_TOKENS,
                web_search=False
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при обработке изображения: {str(e)}" 