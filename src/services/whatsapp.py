import logging
from typing import Dict
import aiohttp
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class WhatsAppAPI:
    def __init__(self, api_key: str, base_url: str = "https://api.wasapi.io/prod/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=self.headers)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_message(self, wa_id: str, message: str) -> Dict:
        """Send WhatsApp message with retry logic"""
        payload = {
            "message": message,
            "wa_id": wa_id
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/whatsapp-messages",
                json=payload
            ) as response:
                if response.status not in (200, 201):
                    logger.error(f"Error sending message: Status {response.status}")
                    raise HTTPException(status_code=response.status, detail="WhatsApp API error")
                return await response.json()
        except Exception as e:
            logger.error(f"Error sending message to {wa_id}: {str(e)}")
            raise

    async def close(self):
        """Cleanup resources"""
        await self.session.close()