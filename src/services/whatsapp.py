# src/services/whatsapp.py
import logging
from typing import Dict
import aiohttp
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import Config

logger = logging.getLogger(__name__)

class WhatsAppAPI:
    def __init__(self, api_key: str = Config.WASAPI_API_KEY, base_url: str = Config.WASAPI_BASE_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_message(self, wa_id: str, message: str) -> Dict:
        payload = {"message": message, "wa_id": wa_id}
        url = f"{self.base_url}/whatsapp-messages"

        async with aiohttp.ClientSession(headers=self.headers) as session:
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
