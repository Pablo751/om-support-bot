import os

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    WASAPI_BASE_URL = os.getenv("WASAPI_BASE_URL", "https://api.wasapi.io/prod/api/v1")
    WASAPI_API_KEY = os.getenv("WASAPI_API_KEY", "")
    KNOWLEDGE_BASE_PATH = 'data/knowledge_base.json'
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
    MONGO_USERNAME = "juanpablo_casado"
    MONGO_HOST = "legacy-production-v6.dmjt9.mongodb.net"
    MONGO_DB = "yom-production"
    MONGO_URL_TEMPLATE = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}/{MONGO_DB}?retryWrites=true&w=majority"