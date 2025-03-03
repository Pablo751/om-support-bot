import logging
from datetime import datetime
from src.services.whatsapp import WhatsAppAPI
from src.services.zoho import ZohoAPI
from src.tools import clean_text

logger = logging.getLogger(__name__)

class Message:
    def __init__(self, api, id, userid, query, type):
        self.api = api
        self.id = id
        self.userid = userid
        self.query = query
        self.type = type

    def reply(self, response_text):
        try:
            logger.info(f"Sending message: {response_text}")
            return self.api.send_message(self.userid, response_text)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    def create_ticket(self, subject, description):
        api_zoho = ZohoAPI()
        return api_zoho.create_ticket(subject, description)
    
class WhatsappMessage(Message):
    def __init__(self, body):
        data = body.get('data', {})
        api = WhatsAppAPI()
        id = data.get('wam_id')
        userid = data.get('wa_id')
        historical_messages = api.get_messages(userid).get('data')
        historical_messages.sort(key=lambda msg: datetime.strptime(msg.get('created_at'), "%Y-%m-%d %H:%M:%S"))
        query = ""
        for historical_message in historical_messages:
            created_at = datetime.strptime(historical_message.get('created_at'), "%Y-%m-%d %H:%M:%S").date()
            today = datetime.today().date()
            if created_at >= today:
                query += f"{historical_message.get('created_at')}: {'Cliente' if historical_message.get('type') == 'in' else 'Yom'}: \n{historical_message.get('message')}\n\n"
        super().__init__(api=api, id=id, userid=userid, query=query, type='whatsapp')

class ZohoMessage(Message):
    def __init__(self, body):
        data = body[0].get('payload', {})
        subject = clean_text(data.get("subject"))
        description = clean_text(data.get("description"))
        custom_fields = data.get("customFields", {})
        client_name = clean_text(custom_fields.get("Organizaci\u00f3n"))
        compiled_query = (
            f"CLIENTE: {client_name}\n\n"
            f"TITULO: {subject}\n\n"
            f"DESCRIPCION:\n{description}"
        )
        super().__init__(
            api=ZohoAPI(),
            id=None,
            userid=data.get('id'),
            query=compiled_query,
            type='zoho'
        )
