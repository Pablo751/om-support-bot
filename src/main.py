import os
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from src.models.schemas import MessageResponse
from src.services.support import EnhancedSupportSystem
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

    if not os.path.exists("data/knowledge_base.csv"):
        logger.warning("CSV knowledge_base.csv not found! The bot will fallback to minimal CSV data.")
    if not os.path.exists("data/knowledge_base.json"):
        logger.warning("JSON knowledge_base.json not found! The bot may fallback to minimal JSON data.")

    # Change to EnhancedSupportSystem
    support_system = EnhancedSupportSystem(
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

        # Extract message data and metadata
        data = body.get('data', {})
        if data:  # Wasapi format
            logger.info("Wasapi format detected")
            message = data.get('message', '')
            wa_id = data.get('wa_id', '')
            wam_id = data.get('wam_id', '')
            # Extract agent information
            message_metadata = {
                'from_agent': data.get('from_agent', False),
                'agent_id': data.get('agent_id'),
                'timestamp': datetime.now().isoformat()
            }
        else:  # Test format
            logger.info("Test format detected")
            message = body.get('message', '')
            wa_id = body.get('wa_id', '')
            wam_id = body.get('wam_id', '')
            message_metadata = {'from_agent': False}

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
        
        # Updated process_query call with new parameters
        response_text, _ = await support_system.process_query(
            query=message,
            wa_id=wa_id,
            message_metadata=message_metadata,
            user_name=None
        )

        # Only send response if we got one (bot might be silent if human is handling)
        if response_text:
            logger.info(f"Generated response: {response_text}")
            logger.info(f"Attempting to send to wa_id: {wa_id}")
            response = await whatsapp_api.send_message(wa_id, response_text)
            logger.info(f"Wasapi send response: {response}")
        else:
            logger.info("No response generated (conversation likely handled by human)")

        return {
            "success": True,
            "info": "Message processed successfully",
            "response_text": response_text
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}

@app.get("/debug/messages")
async def get_debug_info():
    """Get information about processed messages"""
    return {
        "processed_messages_count": len(processed_message_ids),
        "last_10_messages": list(processed_message_ids)[-10:] if processed_message_ids else []
    }

@app.post("/debug/clear-messages")
async def clear_processed_messages():
    """Clear the processed messages set"""
    processed_message_ids.clear()
    return {"success": True, "message": "Processed messages cleared"}

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
