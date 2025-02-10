# src/config.py
import os
from typing import Dict, Any
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    WASAPI_API_KEY: str
    OPENAI_API_KEY: str

    # MongoDB Settings
    MONGO_USERNAME: str = "juanpablo_casado"
    MONGO_PASSWORD: str
    MONGO_URI: str = None

    # Application Settings
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # OpenAI Settings
    OPENAI_MODEL: str = "gpt-4o-mini"
    MAX_TOKENS: int = 150
    TEMPERATURE: float = 0.7

    # WhatsApp Settings
    WHATSAPP_API_BASE_URL: str = "https://api.wasapi.io/prod/api/v1"
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 4

    # File Paths
    KNOWLEDGE_BASE_CSV: str = "data/knowledge_base.csv"
    KNOWLEDGE_BASE_JSON: str = "data/knowledge_base.json"

    def get_mongo_uri(self) -> str:
        if not self.MONGO_URI:
            self.MONGO_URI = f"mongodb+srv://{self.MONGO_USERNAME}:{self.MONGO_PASSWORD}@legacy-production-v6.dmjt9.mongodb.net/yom-production?retryWrites=true&w=majority"
        return self.MONGO_URI

    class Config:
        env_file = ".env"

settings = Settings()