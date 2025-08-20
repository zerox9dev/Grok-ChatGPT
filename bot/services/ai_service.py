import base64
from typing import Dict, List, Optional

import openai
import anthropic

from config import MAX_COMPLETION_TOKENS, OPENAI_API_KEY, ANTHROPIC_API_KEY


class AIService:
    def __init__(self, model_name: str = None):
        """
        Инициализирует сервис для работы с моделями ИИ через официальные API
        
        Args:
            model_name: Название модели (если None, будет использоваться gpt-4o-mini)
        """
        self.model_name = model_name or "gpt-4o-mini"
        
        # Инициализируем клиенты
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Инициализируем Anthropic клиент только если есть API ключ
        self.anthropic_client = None
        if ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    def is_claude_model(self) -> bool:
        """Проверяет, является ли текущая модель Claude"""
        return self.model_name and "claude" in self.model_name.lower()
    
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
        try:
            if context is None:
                context = []
                
            messages = context + [{"role": "user", "content": message}]
            
            # Добавляем системный промпт в начало, если он есть
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            if self.is_claude_model():
                return await self._get_claude_response(messages, system_prompt)
            else:
                return await self._get_openai_response(messages)
                
        except Exception as e:
            return f"Ошибка при получении ответа: {str(e)}"
    
    async def _get_openai_response(self, messages: List[Dict[str, str]]) -> str:
        """Получает ответ от OpenAI модели"""
        params = {
            "model": self.model_name,
            "messages": messages,
            "max_completion_tokens": MAX_COMPLETION_TOKENS  # GPT-5 использует max_completion_tokens
            # GPT-5 использует только дефолтный temperature (1)
        }
        
        response = self.openai_client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    async def _get_claude_response(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Получает ответ от Claude модели"""
        if not self.anthropic_client:
            return "Ошибка: API ключ Anthropic не настроен"
        
        # Для Claude нужно отдельно передавать системный промпт
        claude_messages = [msg for msg in messages if msg["role"] != "system"]
        
        response = self.anthropic_client.messages.create(
            model=self.model_name,
            max_tokens=MAX_COMPLETION_TOKENS,  # Claude использует max_tokens
            messages=claude_messages,
            system=system_prompt if system_prompt else ""
        )
        return response.content[0].text
    
    async def read_image(self, image_path: str) -> str:
        """
        Анализирует изображение с помощью выбранной модели через официальные API
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Текстовое описание изображения
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
            
            if self.is_claude_model():
                return await self._analyze_image_claude(encoded_image)
            else:
                return await self._analyze_image_openai(encoded_image)
                
        except Exception as e:
            return f"Ошибка при обработке изображения: {str(e)}"
    
    async def _analyze_image_openai(self, encoded_image: str) -> str:
        """Анализирует изображение через OpenAI"""
        # GPT-5 поддерживает анализ изображений из коробки
        model = self.model_name
        
        params = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [{
                    "type": "text", 
                    "text": "Опиши это изображение:"
                }, {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
                }]
            }],
            "max_completion_tokens": MAX_COMPLETION_TOKENS  # GPT-5 использует max_completion_tokens
            # GPT-5 использует только дефолтный temperature (1)
        }
        
        response = self.openai_client.chat.completions.create(**params)
        return response.choices[0].message.content
    
    async def _analyze_image_claude(self, encoded_image: str) -> str:
        """Анализирует изображение через Claude"""
        if not self.anthropic_client:
            return "Ошибка: API ключ Anthropic не настроен"
        
        response = self.anthropic_client.messages.create(
            model=self.model_name,
            max_tokens=MAX_COMPLETION_TOKENS,  # Claude использует max_tokens
            messages=[{
                "role": "user",
                "content": [{
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
            }]
        )
        return response.content[0].text