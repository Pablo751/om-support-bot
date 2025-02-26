import logging
from src.services.openai import OpenAIAPI
from src.services.databases import MongoService, KnowledgeBase
import src.texts as texts

logger = logging.getLogger(__name__)

class SupportBot:
    def __init__(self):
        self.openai = OpenAIAPI()
        self.mongo_service = MongoService()
        self.knowledge_service = KnowledgeBase()
        self.system_instructions = texts.SYSTEM_INSTRUCTIONS

    async def process_query(self, message):
        self.message = message
        logger.info(f"Sending request to OpenAI query: {self.message.query}")
        query_response = self.openai.analyze_query(
            self.system_instructions, 
            self.knowledge_service.load_and_build_knowledge(self.message.type), 
            self.message.query
        )
        logger.info(f"Generated query response: {query_response}")

        act_response = await self.act(query_response)
        logger.info(f"Generated action response: {act_response}")

        return act_response

    async def act(self, query_response):
        process_again = query_response.get("process_again", False)
        query_type = query_response.get("query_type")
        act_response = query_response.get('response_text')
        client_name = query_response.get("client_name")
        commerce_id = query_response.get("commerce_id")

        if query_type == "STORE_STATUS":
            if not client_name or not commerce_id:
                act_response = texts.STORE_STATUS_MISSING_MSG
            else:
                store_status = self.mongo_service.check_store_status(client_name, commerce_id)
                if store_status is None:
                    act_response = texts.STORE_STATUS_NOT_FOUND_MSG
                elif store_status:
                    act_response = texts.STORE_STATUS_ACTIVE_MSG.format(commerce_id=commerce_id, client_name=client_name)
                else:
                    act_response = texts.STORE_STATUS_INACTIVE_MSG.format(commerce_id=commerce_id, client_name=client_name)
            
        if process_again:
            self.message.query += act_response
            return await self.process_query(self.message)
        
        send_response = await self.message.send_message(act_response)
        logger.info(f"Send response: {send_response}")

        return act_response
    