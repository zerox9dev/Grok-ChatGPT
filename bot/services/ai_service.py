import base64
from typing import Dict, List, Optional, Any, Union
from functools import wraps

import openai
import anthropic

from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GPT_MODEL, MAX_TOKENS
from bot.utils.logger import setup_logger


# ================================================
# Константы для сообщений
# ================================================
IMAGE_ANALYSIS_PROMPT = "Опиши это изображение:"
ERROR_ANTHROPIC_KEY_MISSING = "Ошибка: API ключ Anthropic не настроен"
ERROR_OPERATION_FAILED = "Ошибка при выполнении операции"

# ================================================
# Логгер для сервиса ИИ
# ================================================
logger = setup_logger(__name__)




def error_handler(func):
    # Декоратор для унификации обработки ошибок
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            # Проверяем что результат не пустой
            if not result or not str(result).strip():
                logger.warning("🚨 ПУСТОЙ ОТВЕТ ОТ НЕЙРОСЕТИ:")
                logger.warning(f"   Тип результата: {type(result)}")
                logger.warning(f"   Значение: {repr(result)}")
                logger.warning(f"   Длина: {len(str(result)) if result else 0}")
                logger.warning(f"   Функция: {func.__name__}")
                return "Нейросеть вернула пустой ответ. Попробуйте переформулировать вопрос."
            return result
        except Exception as e:
            return f"{ERROR_OPERATION_FAILED}: {str(e)}"
    return wrapper


class AIService:
    
    def __init__(self, model_name: str = None):
        # Инициализирует сервис для работы с моделями ИИ через официальные API
        # model_name: Название модели (если None, будет использоваться GPT_MODEL из конфигурации)
        self.model_name = model_name or GPT_MODEL
        
        # ================================================
        # Инициализация клиентов
        # ================================================
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
    
    def is_claude_model(self) -> bool:
        # Проверяет, является ли текущая модель Claude
        return self.model_name and "claude" in self.model_name.lower()
    
    def _prepare_messages(
        self, content: Union[str, List[Dict]], context: List[Dict[str, str]] = None, 
        system_prompt: str = None
    ) -> List[Dict[str, str]]:
        # Унифицированная подготовка сообщений для всех типов контента
        if context is None:
            context = []
        
        # Фильтруем контекст от пустых сообщений
        filtered_context = []
        for msg in context:
            if msg.get("content") and str(msg["content"]).strip():
                filtered_context.append(msg)
            
        user_message = {"role": "user", "content": content}
        messages = filtered_context + [user_message]
        
        if system_prompt and system_prompt.strip():
            messages.insert(0, {"role": "system", "content": system_prompt.strip()})
        
        return messages
    
    @error_handler
    async def _make_api_call(
        self, messages: List[Dict[str, str]], system_prompt: str = None
    ) -> str:
        # Универсальный метод для API вызовов к любому провайдеру
        logger.info(f"📤 Отправляем запрос к нейросети:")
        logger.info(f"   Модель: {self.model_name}")
        logger.info(f"   Количество сообщений: {len(messages)}")
        
        # Для Claude логируем системный промпт отдельно, для OpenAI он уже в messages
        if self.is_claude_model():
            logger.debug(f"   Системный промпт (Claude): {repr(system_prompt)}")
        
        for i, msg in enumerate(messages):
            logger.debug(f"   Сообщение {i+1}: {msg['role']} -> {repr(msg['content'][:100])}{'...' if len(str(msg['content'])) > 100 else ''}")
        
        if self.is_claude_model():
            if not self.anthropic_client:
                return ERROR_ANTHROPIC_KEY_MISSING
            
            # Убираем системный промпт из сообщений для Claude
            claude_messages = [msg for msg in messages if msg["role"] != "system"]
            
            response = self.anthropic_client.messages.create(
                model=self.model_name,
                max_tokens=MAX_TOKENS,
                messages=claude_messages,
                system=system_prompt or ""
            )
            result = response.content[0].text
            logger.info(f"🤖 Claude API ответ:")
            logger.debug(f"   Модель: {self.model_name}")
            logger.debug(f"   Тип response.content: {type(response.content)}")
            logger.debug(f"   Длина content: {len(response.content)}")
            logger.debug(f"   Первый элемент: {repr(response.content[0]) if response.content else 'None'}")
            logger.debug(f"   Текст результата: {repr(result)}")
            logger.debug(f"   Длина текста: {len(result) if result else 0}")
            return result
        else:
            # OpenAI
            params = {
                "model": self.model_name,
                "messages": messages,
                "max_completion_tokens": MAX_TOKENS
            }
            
            response = self.openai_client.chat.completions.create(**params)
            result = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            logger.info(f"🤖 OpenAI API ответ:")
            logger.debug(f"   Модель: {self.model_name}")
            logger.debug(f"   Finish reason: {finish_reason}")
            logger.debug(f"   Тип choices: {type(response.choices)}")
            logger.debug(f"   Длина choices: {len(response.choices)}")
            logger.debug(f"   Первый choice: {repr(response.choices[0]) if response.choices else 'None'}")
            logger.debug(f"   Текст результата: {repr(result)}")
            logger.debug(f"   Длина текста: {len(result) if result else 0}")
            
            # Проверяем причину завершения
            if finish_reason == 'length':
                return f"⚠️ Ответ был обрезан из-за лимита токенов. Попробуйте задать более короткий вопрос или очистите историю командой /reset."
            
            return result
    
    async def get_response(
        self, message: str, context: List[Dict[str, str]] = None, system_prompt: str = None
    ) -> str:
        # Получает ответ от выбранной модели ИИ через официальные API
        # message: Текст сообщения пользователя, context: Контекст предыдущей беседы
        # system_prompt: Системный промпт для модели
        messages = self._prepare_messages(message, context, system_prompt)
        # Для Claude передаем system_prompt отдельно, для OpenAI он уже в messages
        claude_system_prompt = system_prompt if self.is_claude_model() else None
        return await self._make_api_call(messages, claude_system_prompt)
    
    def _create_image_content(self, encoded_image: str) -> List[Dict]:
        # Создает контент сообщения с изображением для разных API
        if self.is_claude_model():
            return [{
                "type": "text",
                "text": IMAGE_ANALYSIS_PROMPT
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
                "text": IMAGE_ANALYSIS_PROMPT
            }, {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
            }]
    
    @error_handler
    async def read_image(self, image_path: str) -> str:
        # Анализирует изображение с помощью выбранной модели через официальные API
        # image_path: Путь к файлу изображения
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        image_content = self._create_image_content(encoded_image)
        messages = self._prepare_messages(image_content)
        return await self._make_api_call(messages)