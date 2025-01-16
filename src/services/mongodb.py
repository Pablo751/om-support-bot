# src/services/mongodb.py
import os
import logging
import certifi
from typing import Optional
from pymongo import MongoClient

logger = logging.getLogger(__name__)

class MongoDBService:
    def __init__(self):
        self.username = os.getenv('MONGO_USERNAME', 'juanpablo_casado')
        self.password = os.getenv('MONGO_PASSWORD')
        self.client = None

    def _get_client(self) -> Optional[MongoClient]:
        """Get MongoDB client with connection pooling"""
        if self.client is None:
            try:
                url = f"mongodb+srv://{self.username}:{self.password}@legacy-production-v6.dmjt9.mongodb.net/yom-production?retryWrites=true&w=majority"
                self.client = MongoClient(
                    url, 
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=5000
                )
                # Test connection
                self.client.admin.command('ping')
                logger.info("MongoDB connection successful.")
            except Exception as e:
                logger.error(f"Error connecting to MongoDB: {e}")
                self.client = None
                raise
        return self.client

    def check_store_status(self, company_name: str, store_id: str) -> Optional[bool]:
        """Check store status in MongoDB"""
        filter_json = {
            "domain": f"{company_name}.youorder.me",
            "contact.externalId": store_id
        }
        
        try:
            client = self._get_client()
            if not client:
                return None
                
            db = client['yom-production']
            collection = db['commerces']
            
            store = collection.find_one(filter_json)
            logger.info(f"MongoDB search result for {filter_json}: {store}")
            
            if store:
                return store.get('active', False)
            return None
            
        except Exception as e:
            logger.error(f"MongoDB error: {str(e)}")
            return None

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None