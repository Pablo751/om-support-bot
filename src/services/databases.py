import certifi
import logging
from typing import Optional
from pymongo import MongoClient
from src.config import Config
import json

logger = logging.getLogger(__name__)
        
class KnowledgeBase:
    def __init__(self):
        self.knowledge_base_path = Config.KNOWLEDGE_BASE_PATH

    def load_and_build_knowledge(self) -> str:
        with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        knowledge = ""
        for item in knowledge_base.get("faq", []):
            knowledge += f"Pregunta: \n{item['question']}\n"
            knowledge += f"Respuesta: \n{item['answer']}\n"
            knowledge += "-" * 50 + "\n"
        return knowledge    

class MongoService:    
    def __init__(self):
        self.client = None

    def get_client(self):
        url = Config.MONGO_URL_TEMPLATE.format(username=Config.MONGO_USERNAME, password=Config.MONGO_PASSWORD)
        self.client = MongoClient(url)
        return self.client

    def check_store_status(self, company_name, commerce_id, db_name = Config.MONGO_DB):
        filter_json = {
            "domain": f"{company_name.lower()}.youorder.me",
            "contact.externalId": str(commerce_id)
        }

        client = self.get_client()
        db = client[db_name]
        collection = db['commerces']
        store = collection.find_one(filter_json)
        logger.info(f"MongoDB search result for {filter_json}: {store}")

        if not store:
            return None
        
        return store.get('active', False)