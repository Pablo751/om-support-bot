import logging
import random
from fastapi import HTTPException
from src.services.openai import OpenAIAPI
from src.services.databases import MongoService, KnowledgeBase
from src.services.whatsapp import WhatsAppAPI
import src.texts as texts

logger = logging.getLogger(__name__)

class SupportBot:
    def __init__(self):
        self.openai = OpenAIAPI()
        self.whatsapp_api = WhatsAppAPI()
        self.mongo_service = MongoService()
        self.knowledge = KnowledgeBase().load_and_build_knowledge()
        self.processed_message_ids = set()
        self.system_instruction = texts.SYSTEM_INSTRUCTION
        self.prompt = texts.PROMPT_TEMPLATE
        self.wa_id = None
        self.wam_id = None
        self.message = None
    
    async def start(self, body):
        data = body['data']
        self.message = data.get('message')
        self.wa_id = data.get('wa_id')
        self.wam_id = data.get('wam_id')

        if not self.wa_id or not self.wam_id or not self.message:
            error_msg = "Missing message, wa_id or wam_id"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        if self.wam_id in self.processed_message_ids:
            msg = f"Duplicate message with wam_id={self.wam_id}, skipping."
            logger.info(msg)
            return msg
        else:
            self.processed_message_ids.add(self.wam_id)

        response = await self.process_query(self.message)
        
        return response

    async def process_query(self, query, response=None):
        logger.info(f"Sending requesst to OpenAI query: {query}")
        try:
            response = self.openai.analyze_query(self.system_instruction, self.prompt.format(query=query, knowledge=self.knowledge))
        except Exception:
            response = texts.TECHNICAL_ISSUE_MSG
            logger.error(response, exc_info=True)
        logger.info(f"Generated query response: {response}")

        act_response = await self.act(query, response)
        logger.info(f"Generated action response: {act_response}")

        return act_response

    async def act(self, query, response):
        process_again = False

        query_type = response.get("query_type", "GENERAL")

        if query_type == "STORE_STATUS":
            store_info = response.get("store_info", {})
            company_name = store_info.get("company_name")
            store_id = store_info.get("store_id")

            if not company_name or not store_id:
                return texts.STORE_STATUS_MISSING_MSG, None

            store_status = self.mongo_service.check_store_status(company_name, store_id)
            if store_status is None:
                return texts.STORE_NOT_FOUND_MSG, None
            elif store_status:
                return texts.STORE_ACTIVE_MSG.format(store_id=store_id, company_name=company_name), None
            else:
                return texts.STORE_INACTIVE_MSG.format(store_id=store_id, company_name=company_name), None

        # this one should not be needed
        if query_type == "STORE_STATUS_MISSING":
            return (texts.STORE_STATUS_MISSING_MSG, ["company_name", "store_id"])
        
        if True:
            # Send to WhatsApp
            send_response = await self.whatsapp_api.send_message(self.wa_id, response)
            logger.info(f"WhatsApp send response: {send_response}")

        if process_again:
            return await self.process_query(query, response)
        
        return response
    