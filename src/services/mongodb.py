# src/services/mongodb.py
import os
import logging
import certifi
from typing import Optional, Dict
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.mongo_client import MongoClient

logger = logging.getLogger(__name__)

class MongoDBService:
    def __init__(self):
        self.username = os.getenv('MONGO_USERNAME', 'juanpablo_casado')
        self.password = os.getenv('MONGO_PASSWORD')
        self.sync_client = None
        self.async_client = None
        self.db_name = 'yom-production'
    
    def _get_connection_url(self) -> str:
        return f"mongodb+srv://{self.username}:{self.password}@legacy-production-v6.dmjt9.mongodb.net/{self.db_name}?retryWrites=true&w=majority"
    
    def _get_sync_client(self) -> Optional[MongoClient]:
        """Get synchronous MongoDB client with connection pooling"""
        if self.sync_client is None:
            try:
                url = self._get_connection_url()
                self.sync_client = MongoClient(
                    url,
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=5000
                )
                # Test connection
                self.sync_client.admin.command('ping')
                logger.info("Synchronous MongoDB connection successful.")
            except Exception as e:
                logger.error(f"Error connecting to MongoDB: {e}")
                self.sync_client = None
                raise
        return self.sync_client

    def _get_async_client(self) -> AsyncIOMotorClient:
        """Get asynchronous MongoDB client"""
        if self.async_client is None:
            try:
                url = self._get_connection_url()
                self.async_client = AsyncIOMotorClient(
                    url,
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=5000
                )
                logger.info("Asynchronous MongoDB connection initialized.")
            except Exception as e:
                logger.error(f"Error connecting to async MongoDB: {e}")
                raise
        return self.async_client

    def check_store_status(self, company_name: str, store_id: str) -> Optional[bool]:
        """Synchronous check store status in MongoDB"""
        filter_json = {
            "domain": f"{company_name}.youorder.me",
            "contact.externalId": store_id
        }
        
        try:
            client = self._get_sync_client()
            if not client:
                return None
                
            db = client[self.db_name]
            collection = db['commerces']
            
            store = collection.find_one(filter_json)
            logger.info(f"MongoDB search result for {filter_json}: {store}")
            
            if store:
                return store.get('active', False)
            return None
            
        except Exception as e:
            logger.error(f"MongoDB error: {str(e)}")
            return None

    async def check_store_status_async(self, company_name: str, store_id: str) -> Optional[bool]:
        """Asynchronous check store status in MongoDB"""
        filter_json = {
            "domain": f"{company_name}.youorder.me",
            "contact.externalId": store_id
        }
        
        try:
            client = self._get_async_client()
            db = client[self.db_name]
            collection = db['commerces']
            
            store = await collection.find_one(filter_json)
            logger.info(f"MongoDB async search result for {filter_json}: {store}")
            
            if store:
                return store.get('active', False)
            return None
            
        except Exception as e:
            logger.error(f"MongoDB async error: {str(e)}")
            return None

    async def get_conversation_state(self, wa_id: str) -> Dict:
        """Get or create conversation state"""
        try:
            client = self._get_async_client()
            db = client[self.db_name]
            collection = db['conversation_states']
            
            state = await collection.find_one({"wa_id": wa_id})
            if not state:
                state = {
                    "wa_id": wa_id,
                    "state": "bot",
                    "assigned_agent": None,
                    "last_update": datetime.utcnow(),
                    "handover_reason": None
                }
                await collection.insert_one(state)
            return state
            
        except Exception as e:
            logger.error(f"MongoDB async error: {str(e)}")
            return None

    async def update_conversation_state(self, wa_id: str, update_data: Dict) -> bool:
        """Update conversation state"""
        try:
            client = self._get_async_client()
            db = client[self.db_name]
            collection = db['conversation_states']
            
            result = await collection.update_one(
                {"wa_id": wa_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"MongoDB async error: {str(e)}")
            return False

    def close(self):
        """Close MongoDB connections"""
        if self.sync_client:
            self.sync_client.close()
            self.sync_client = None
        if self.async_client:
            self.async_client.close()
            self.async_client = None
