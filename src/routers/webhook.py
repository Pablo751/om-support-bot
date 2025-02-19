import logging
from fastapi import APIRouter, Request
from src.services.support_bot import SupportBot
from datetime import datetime
from src.models.messages import WhatsappMessage, ZohoMessage

logger = logging.getLogger(__name__)

webhook_router = APIRouter()

async def process_incoming(message_class, request):
    try:
        logger.info(f"=============== New {message_class.__name__} ===============")
        body = await request.json()
        headers = dict(request.headers)
        logger.info(f"Headers: {headers}")
        logger.info(f"Raw body: {body}")

        message = message_class(body)
        support_bot = SupportBot(message)
        message_response = await support_bot.process_query()

        return {
            "success": True,
            "info": "Message processed successfully",
            "response": message_response
        }
    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        return {
            "success": False,
            "info": "Error processing message"
        }

@webhook_router.post("/webhook")
async def webhook(request: Request):
    return await process_incoming(WhatsappMessage, request)


@webhook_router.post("/zohoTicket")
async def zoho_ticket(request: Request):
    return await process_incoming(ZohoMessage, request)

@webhook_router.get("/health")
async def health_check():
    try:    
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.exception(f"Error processing health check: {e}")
        return {
            "status": "error",
            "info": "Error processing health check"
        }
