import logging
import requests
from fastapi import HTTPException
from src.config import Config

logger = logging.getLogger(__name__)

class WhatsAppAPI:
    def __init__(self):
        self.api_key = Config.WASAPI_API_KEY
        self.base_url = Config.WASAPI_BASE_URL
    
    def send_message(self, wa_id, message):
        payload = {"message": message, "wa_id": wa_id}
        url = f"{self.base_url}/whatsapp-messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                return response.json()
            error_text = response.text
            logger.error(f"Failed to send message to {wa_id}. Status: {response.status_code}, Response: {error_text}")
            raise HTTPException(status_code=response.status_code, detail=error_text)

        except requests.RequestException as e:
            logger.error(f"Network error while sending message to {wa_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Network error while sending message.")

    def get_messages(self, wa_id):
        url = f"{self.base_url}/whatsapp-messages/{wa_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)
        return response.json()