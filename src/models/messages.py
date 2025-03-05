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
        self.manual_mode = False

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
        id = data.get('wam_id')
        userid = data.get('wa_id')

        api = WhatsAppAPI()
        historical_messages = api.get_messages(userid).get('data')
        historical_messages.sort(key=lambda msg: datetime.strptime(msg.get('created_at'), "%Y-%m-%d %H:%M:%S"))
        query = ""
        for historical_message in historical_messages:
            created_at = datetime.strptime(historical_message.get('created_at'), "%Y-%m-%d %H:%M:%S").date()
            today = datetime.today().date()
            if created_at >= today:
                query += f"{'Cliente' if historical_message.get('type') == 'in' else 'Yom'}: \n{historical_message.get('message')}\n\n"
        
        self.manual_mode = self.is_manual_mode(historical_messages)
        
        super().__init__(api=api, id=id, userid=userid, query=query, type='whatsapp')
    
    def is_manual_mode(self, historical_messages):
        # if the two messages before the last one are from us, it means someone started interacting with the user manually, therefore the bot shouldn't reply
        if (
            len(historical_messages) >= 3 and
            historical_messages[-1].get('type') == 'in' and
            historical_messages[-2].get('type') == 'out' and
            historical_messages[-3].get('type') == 'out'
        ):
            return True
        # once manual mode is activated, it should not be deactivated again
        return self.manual_mode

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
