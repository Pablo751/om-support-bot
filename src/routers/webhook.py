import logging
from fastapi import APIRouter, Request
from src.services.support_bot import SupportBot
from datetime import datetime

logger = logging.getLogger(__name__)

webhook_router = APIRouter()

@webhook_router.post("/webhook")
async def webhook(request: Request):
    try:
        logger.info("=============== NEW WEBHOOK REQUEST ===============")
        body = await request.json()
        headers = dict(request.headers)
        logger.info(f"Headers: {headers}")
        logger.info(f"Raw body: {body}")

        support_bot = SupportBot()

        response_text = await support_bot.start(body)

        return {
            "success": True,
            "info": "Message processed successfully",
            "response_text": response_text
        }
    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        return {
            "success": False,
            "info": "Error processing message"
        }

@webhook_router.post("/zohoTicket")
async def health_check(request):
    try:
        logger.info("=============== NEW ZOHO TICKET ===============")
        body = await request.json()
        headers = dict(request.headers)
        logger.info(f"Headers: {headers}")
        logger.info(f"Raw body: {body}")
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.exception(f"Error processing zoho ticket: {e}")
        return {
            "status": "error",
            "info": "Error processing zoho ticket"
        }

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
