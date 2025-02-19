import logging
from fastapi import HTTPException
from src.services.openai import OpenAIAPI
from src.services.databases import MongoService, KnowledgeBase
from src.services.whatsapp import WhatsAppAPI
from src.services.zoho import ZohoAPI
import src.texts as texts

logger = logging.getLogger(__name__)

class SupportBot:
    def __init__(self):
        self.openai = OpenAIAPI()
        self.whatsapp_api = WhatsAppAPI()
        self.zoho_api = ZohoAPI()
        self.mongo_service = MongoService()
        self.knowledge_service = KnowledgeBase()
        self.system_instructions = texts.SYSTEM_INSTRUCTION
        self.knowledge = texts.KNOWLEDGE.format(knowledge=self.knowledge_service.load_and_build_knowledge())
        self.processed_message_ids = set()
        self.query = None
        self.wa_id = None
        self.wam_id = None
        self.ticket_id = None
    
    async def start_zoho(self, body):
        data = body[0].get('payload', {})
        subject = data.get('subject', 'No Subject')
        description = data.get('description', 'No Description')
        self.query = f"{subject}: {description}"
        self.ticket_id = data.get('id', None)
        
        response = await self.process_query()

        return response

    async def start_whatsapp(self, body):
        data = body['data']
        self.query = data.get('message')
        self.wa_id = data.get('wa_id')
        self.wam_id = data.get('wam_id')

        if not self.wa_id or not self.wam_id or not self.query:
            error_msg = "Missing message, wa_id or wam_id"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        if self.wam_id in self.processed_message_ids:
            msg = f"Duplicate message with wam_id={self.wam_id}, skipping."
            logger.info(msg)
            return msg
        else:
            self.processed_message_ids.add(self.wam_id)

        response = await self.process_query()
        
        return response

    async def process_query(self):
        logger.info(f"Sending requesst to OpenAI query: {self.query}")
        try:
            response = self.openai.analyze_query(self.system_instructions, self.knowledge, self.query)
        except Exception:
            response = texts.TECHNICAL_ISSUE_MSG
            logger.error(response, exc_info=True)
        logger.info(f"Generated query response: {response}")

        act_response = await self.act(response)
        logger.info(f"Generated action response: {act_response}")

        return act_response

    async def act(self, response):
        response_text = response.get('response_text')
        process_again = response.get("process_again", False)

        query_type = response.get("query_type", "GENERAL")

        if query_type == "STORE_STATUS":
            store_info = response.get("store_info", {})
            company_name = store_info.get("company_name")
            store_id = store_info.get("store_id")

            if not company_name or not store_id:
                return texts.STORE_STATUS_MISSING_MSG

            store_status = self.mongo_service.check_store_status(company_name, store_id)
            if store_status is None:
                return texts.STORE_NOT_FOUND_MSG
            elif store_status:
                return texts.STORE_ACTIVE_MSG.format(store_id=store_id, company_name=company_name)
            else:
                return texts.STORE_INACTIVE_MSG.format(store_id=store_id, company_name=company_name)

        # this one should not be needed
        if query_type == "STORE_STATUS_MISSING":
            return texts.STORE_STATUS_MISSING_MSG
        
        # Send to WhatsApp
        send_response = None
        if self.wa_id and self.wam_id and self.query: # poor practice
            send_response = await self.whatsapp_api.send_message(self.wa_id, response_text)
            logger.info(f"WhatsApp send response: {send_response}")
        # Send to Zoho
        else: # poor practice
            send_response = await self.zoho_api.send_message(self.ticket_id, response_text)
            logger.info(f"Zoho send response: {send_response}")

        if process_again:
            self.query += response_text
            return await self.process_query()
        
        return response_text
    