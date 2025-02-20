import logging
from src.services.whatsapp import WhatsAppAPI
from src.services.zoho import ZohoAPI
from src.tools import clean_text

logger = logging.getLogger(__name__)

class Message:
    def __init__(self, api, id, query):
        self.api = api
        self.id = id
        self.query = query

    async def reply(self, response_text):
        try:
            logger.info(f"Sending message: {response_text}")
            return await self.api.send_message(self.id, response_text)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
class WhatsappMessage(Message):
    def __init__(self, body):
        data = body['data']
        super().__init__(
            api=WhatsAppAPI(),
            id=data.get('wa_id'),
            query=data.get('message')
        )

class ZohoMessage(Message):
    def __init__(self, body):
        data = body[0].get('payload', {})
        subject = clean_text(data.get('subject'))
        description = clean_text(data.get('description'))
        client = clean_text(data.get('customFields').get('Organizaci\u00f3n'))
        super().__init__(
            api=ZohoAPI(),
            id=data.get('id'),
            query=f"CLIENTE: {client}\n\nTITULO: {subject}\n\nDESCRIPCION: \n{description}"
        )