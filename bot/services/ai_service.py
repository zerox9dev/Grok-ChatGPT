import base64
from typing import Dict, List, Optional, Any, Union
from functools import wraps

import openai
import anthropic

from config import OPENAI_API_KEY, ANTHROPIC_API_KEY


def error_handler(func):
    """Декоратор для унификации обработки ошибок"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return f"Ошибка при выполнении операции: {str(e)}"
    return wrapper


class AIService:
    # ================================================
    # Конфигурация API параметров
    # ================================================
    MAX_TOKENS = 1000
    DEFAULT_MODEL = "gpt-5"
    
    def __init__(self, model_name: str = None):
        """
        Инициализирует сервис для работы с моделями ИИ через официальные API
        
        Args:
            model_name: Название модели (если None, будет использоваться DEFAULT_MODEL)
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        
        # ================================================
        # Инициализация клиентов
        # ================================================
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
    
    def is_claude_model(self) -> bool:
        """Проверяет, является ли текущая модель Claude"""
        return self.model_name and "claude" in self.model_name.lower()
    
    def _prepare_messages(
        self, content: Union[str, List[Dict]], context: List[Dict[str, str]] = None, 
        system_prompt: str = None
    ) -> List[Dict[str, str]]:
        """Унифицированная подготовка сообщений для всех типов контента"""
        if context is None:
            context = []
            
        user_message = {"role": "user", "content": content}
        messages = context + [user_message]
        
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        return messages
    
    @error_handler
    async def _make_api_call(
        self, messages: List[Dict[str, str]], system_prompt: str = None
    ) -> str:
        """Универсальный метод для API вызовов к любому провайдеру"""
        if self.is_claude_model():
            if not self.anthropic_client:
                return "Ошибка: API ключ Anthropic не настроен"
            
            # Убираем системный промпт из сообщений для Claude
            claude_messages = [msg for msg in messages if msg["role"] != "system"]
            
            response = self.anthropic_client.messages.create(
                model=self.model_name,
                max_tokens=self.MAX_TOKENS,
                messages=claude_messages,
                system=system_prompt or ""
            )
            return response.content[0].text
        else:
            # OpenAI
            params = {
                "model": self.model_name,
                "messages": messages,
                "max_completion_tokens": self.MAX_TOKENS
            }
            
            response = self.openai_client.chat.completions.create(**params)
            return response.choices[0].message.content
    
    async def get_response(
        self, message: str, context: List[Dict[str, str]] = None, system_prompt: str = None
    ) -> str:
        """
        Получает ответ от выбранной модели ИИ через официальные API
        
        Args:
            message: Текст сообщения пользователя
            context: Контекст предыдущей беседы
            system_prompt: Системный промпт для модели
            
        Returns:
            Текстовый ответ от модели
        """
        messages = self._prepare_messages(message, context, system_prompt)
        return await self._make_api_call(messages, system_prompt)
    
    def _create_image_content(self, encoded_image: str) -> List[Dict]:
        """Создает контент сообщения с изображением для разных API"""
        if self.is_claude_model():
            return [{
                "type": "text",
                "text": "Опиши это изображение:"
            }, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encoded_image
                }
            }]
        else:
            return [{
                "type": "text", 
                "text": "Опиши это изображение:"
            }, {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
            }]
    
    @error_handler
    async def read_image(self, image_path: str) -> str:
        """
        Анализирует изображение с помощью выбранной модели через официальные API
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Текстовое описание изображения
        """
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        image_content = self._create_image_content(encoded_image)
        messages = self._prepare_messages(image_content)
        return await self._make_api_call(messages)