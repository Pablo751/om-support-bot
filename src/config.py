import os

class Config:
    # OPENAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # WHATSAPP
    WASAPI_BASE_URL = os.getenv("WASAPI_BASE_URL")
    WASAPI_API_KEY = os.getenv("WASAPI_API_KEY")

    # ZOHO
    ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
    ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
    ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
    ZOHO_TOKEN_URL = os.getenv("ZOHO_TOKEN_URL")
    ZOHO_ORG_ID = os.getenv("ZOHO_ORG_ID")
    ZOHO_DEPARTMENT_ID = os.getenv("ZOHO_DEPARTMENT_ID")
    ZOHO_DESK_DOMAIN = os.getenv("ZOHO_DESK_DOMAIN")

    # MONGO
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
    MONGO_USERNAME = os.getenv("MONGO_USERNAME")
    MONGO_HOST = os.getenv("MONGO_HOST")
    MONGO_DB = os.getenv("MONGO_DB")
    MONGO_URL_TEMPLATE = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}/{MONGO_DB}?retryWrites=true&w=majority"

    # OTHER
    KNOWLEDGE_BASE_PATH = 'data/knowledge_base.json'