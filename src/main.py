# src/main.py
import os
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from src.models.schemas import WebhookRequest, MessageResponse
from src.services.support import SupportSystem
from src.services.whatsapp import WhatsAppAPI
from src.services.mongodb import MongoDBService

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="YOM Support Bot", version="1.0.0")

# Initialize components
support_system = None
whatsapp_api = None
mongodb_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize components with knowledge bases"""
    global support_system, whatsapp_api, mongodb_service

    api_key = os.getenv("WASAPI_API_KEY")
    if not api_key:
        raise ValueError("WASAPI_API_KEY not found in environment variables")

    # Initialize services
    support_system = SupportSystem(
        knowledge_base_csv='data/knowledge_base.csv',
        knowledge_base_json='data/knowledge_base.json'
    )
    whatsapp_api = WhatsAppAPI(api_key)
    mongodb_service = MongoDBService()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if whatsapp_api:
        await whatsapp_api.close()
    if mongodb_service:
        mongodb_service.close()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": str(exc.detail)}
    )

@app.post("/webhook", response_model=MessageResponse)
async def webhook(webhook_request: WebhookRequest):
    """Handle incoming WhatsApp messages"""
    try:
        # Add detailed logging
        logger.info("Received webhook request:")
        logger.info(f"Message: {webhook_request.message}")
        logger.info(f"WhatsApp ID: {webhook_request.wa_id}")

        # Process query and send response
        # Remove the comma after responsetext as it's trying to unpack too many values
        response_text = await support_system.process_query(
            webhook_request.message,
            user_name=None
        )

        logger.info(f"Generated response: {response_text}")
        logger.info(f"Sending response to WhatsApp ID: {webhook_request.wa_id}")

        await whatsapp_api.send_message(webhook_request.wa_id, response_text)

        return {
            "success": True, 
            "info": "Message processed successfully",
            "response_text": response_text
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {
            "success": False, 
            "error": f"Internal server error: {str(e)}",
            "response_text": None
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
