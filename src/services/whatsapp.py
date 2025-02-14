import logging
from typing import Dict
import aiohttp
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import Config

logger = logging.getLogger(__name__)

class WhatsAppAPI:
    def __init__(self):
        self.api_key = Config.WASAPI_API_KEY
        self.base_url = Config.WASAPI_BASE_URL
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_message(self, wa_id, response):
        message = response.get("response_text")
        payload = {"message": message, "wa_id": wa_id}
        url = f"{self.base_url}/whatsapp-messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.post(url, json=payload) as response:
                    if response.status not in (200, 201):
                        error_text = await response.text()
                        logger.error(f"Failed to send message to {wa_id}. Status: {response.status}, Response: {error_text}")
                        raise HTTPException(status_code=response.status, detail=error_text)

                    return await response.json()

            except aiohttp.ClientError as e:
                logger.error(f"Network error while sending message to {wa_id}: {str(e)}")
                raise
