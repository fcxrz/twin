import os
import logging
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        # Используем официальный эндпоинт совместимости OpenAI
        self.client = AsyncOpenAI(
            api_key=os.getenv("AI_API_KEY"),
            base_url="https://router.huggingface.co/v1"
        )
        
        # Модели, которые точно поддерживают этот интерфейс
        self.models = [
            "Qwen/Qwen2.5-7B-Instruct",
            "meta-llama/Llama-3.2-3B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3"
        ]
        self.current_model_idx = 0
        self.max_retries = len(self.models)
    
    @property
    def current_model(self):
        """Возвращает текущую модель"""
        return self.models[self.current_model_idx]
    
    def switch_model(self):
        """Переключается на следующую модель в списке"""
        self.current_model_idx = (self.current_model_idx + 1) % len(self.models)
        logger.info(f"🔄 Переключение на модель: {self.current_model}")
        return self.current_model
    
    def reset_model(self):
        """Сбрасывает индекс модели на первую"""
        self.current_model_idx = 0
    
    async def chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 512):
        """
        Отправляет запрос к модели с автоматическим переключением при ошибке
        
        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            temperature: Температура генерации (0.0 - 1.0)
            max_tokens: Максимальное количество токенов в ответе
        
        Returns:
            str: Ответ модели
        """
        retries = 0
        
        while retries < self.max_retries:
            try:
                response = await self.client.chat.completions.create(
                    model=self.current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Успех — сбрасываем индекс модели на первую
                self.reset_model()
                return response.choices[0].message.content
                
            except Exception as e:
                logger.warning(f"⚠️ Модель {self.current_model} вернула ошибку: {e}")
                retries += 1
                
                if retries < self.max_retries:
                    self.switch_model()
                    logger.info(f"🔄 Попытка {retries + 1}/{self.max_retries} с новой моделью")
                else:
                    logger.error("❌ Все модели недоступны")
                    raise Exception("Все модели недоступны. Попробуйте позже.")
        
        raise Exception("Не удалось получить ответ от AI")
    
    async def test_connection(self):
        """Проверяет подключение к API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.current_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"❌ Тест подключения не пройден: {e}")
            return False