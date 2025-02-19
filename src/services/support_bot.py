import logging
from src.services.openai import OpenAIAPI
from src.services.databases import MongoService, KnowledgeBase
import src.texts as texts

logger = logging.getLogger(__name__)

class SupportBot:
    def __init__(self, message):
        self.openai = OpenAIAPI()
        self.mongo_service = MongoService()
        self.knowledge_service = KnowledgeBase()
        self.system_instructions = texts.SYSTEM_INSTRUCTIONS
        self.message = message

    async def process_query(self):
        logger.info(f"Sending requesst to OpenAI query: {self.message.query}")
        query_response = self.openai.analyze_query(self.system_instructions, self.knowledge_service.load_and_build_knowledge(), self.message.query)
        logger.info(f"Generated query response: {query_response}")

        act_response = await self.act(query_response)
        logger.info(f"Generated action response: {act_response}")

        return act_response

    async def act(self, query_response):
        process_again = query_response.get("process_again", False)
        query_type = query_response.get("query_type", "GENERAL")

        if query_type == "STORE_STATUS":
            store_info = query_response.get("store_info", {})
            company_name = store_info.get("company_name")
            store_id = store_info.get("store_id")

            store_status = self.mongo_service.check_store_status(company_name, store_id)
            if not company_name or not store_id:
                act_response = texts.STORE_STATUS_MISSING_MSG
            elif store_status is None:
                act_response = texts.STORE_NOT_FOUND_MSG
            elif store_status:
                act_response = texts.STORE_ACTIVE_MSG.format(store_id=store_id, company_name=company_name)
            else:
                act_response = texts.STORE_INACTIVE_MSG.format(store_id=store_id, company_name=company_name)
        elif query_type == "STORE_STATUS_MISSING":
            act_response = texts.STORE_STATUS_MISSING_MSG
        else:
            act_response = query_response.get('response_text')
        
        if process_again:
            self.message.query += act_response
            return await self.process_query()

        # Send
        send_response = await self.message.reply(act_response)
        logger.info(f"Send response: {send_response}")

        return act_response
    