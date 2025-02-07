import os
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from src.services.conversation import ConversationHandler, ConversationState
from typing import Optional
from pydantic import BaseModel
from src.models.schemas import MessageResponse
from src.services.support import SupportSystem
from src.services.whatsapp import WhatsAppAPI
from src.services.mongodb import MongoDBService

logger = logging.getLogger(__name__)

app = FastAPI(title="YOM Support Bot", version="1.0.0")

# (2) A simple set to remember processed message IDs, preventing duplicates
processed_message_ids = set()

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

    # (3) Check that the knowledge base files exist
    if not os.path.exists("data/knowledge_base.csv"):
        logger.warning("CSV knowledge_base.csv not found! The bot will fallback to minimal CSV data.")
    if not os.path.exists("data/knowledge_base.json"):
        logger.warning("JSON knowledge_base.json not found! The bot may fallback to minimal JSON data.")

    # Initialize services
    support_system = SupportSystem(
        knowledge_base_csv='data/knowledge_base.csv',
        knowledge_base_json='data/knowledge_base.json'
    )
    whatsapp_api = WhatsAppAPI(api_key)
    mongodb_service = MongoDBService()


@app.post("/webhook", response_model=MessageResponse)
async def webhook(request: Request):
    """Handle incoming WhatsApp messages."""
    try:
        body = await request.json()
        headers = dict(request.headers)
        logger.info("=============== NEW WEBHOOK REQUEST ===============")
        logger.info(f"Headers: {headers}")
        logger.info(f"Raw body: {body}")

        if 'data' in body:
            logger.info("Wasapi format detected")
            logger.info(f"Data content: {body['data']}")
            message = body['data'].get('message', '')
            wa_id = body['data'].get('wa_id', '')
            wam_id = body['data'].get('wam_id', '')
            logger.info(f"Extracted from Wasapi - message: {message}, wa_id: {wa_id}")
        else:
            logger.info("Test format detected")
            message = body.get('message', '')
            wa_id = body.get('wa_id', '')
            wam_id = body.get('wam_id', '')
            logger.info(f"Extracted from test format - message: {message}, wa_id: {wa_id}")

        if not message or not wa_id:
            error_msg = "Missing message or wa_id"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        # Deduplication check
        if wam_id and wam_id in processed_message_ids:
            logger.info(f"Duplicate message with wam_id={wam_id}, skipping.")
            return {
                "success": True,
                "info": "Duplicate message, ignoring repeated webhook."
            }
        processed_message_ids.add(wam_id)

        logger.info(f"About to process query: {message} for wa_id: {wa_id}")
        
        # Process query and check if human handoff needed
        response_text, needs_handoff = await support_system.process_query(
            message,
            user_name=None
        )

        logger.info(f"Generated response: {response_text}")
        logger.info(f"Handoff needed: {needs_handoff}")
        
        # Send response
        response = await whatsapp_api.send_message(wa_id, response_text)
        logger.info(f"Wasapi send response: {response}")
        
        # If handoff is needed, create a ticket
        if needs_handoff:
            ticket = await support_system._create_support_ticket(wa_id, message)
            logger.info(f"Created support ticket: {ticket['_id']}")
        
        return {
            "success": True,
            "info": "Message processed successfully",
            "response_text": response_text,
            "handoff_initiated": needs_handoff
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}

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
