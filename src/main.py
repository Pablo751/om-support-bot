# src/main.py
import os
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from src.models.schemas import MessageResponse
from src.services.support import SupportSystem
from src.services.whatsapp import WhatsAppAPI
from src.services.mongodb import MongoDBService

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
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

@app.post("/webhook", response_model=MessageResponse)
async def webhook(request: Request):
    """Handle incoming WhatsApp messages"""
    try:
        # Get the raw request body
        body = await request.json()
        logger.info(f"Received raw webhook data: {body}")

        # If it's coming from Wasapi, it will have a 'data' field
        if 'data' in body:
            message = body['data'].get('message', '')
            wa_id = body['data'].get('wa_id', '')
        else:
            # Our test format
            message = body.get('message', '')
            wa_id = body.get('wa_id', '')

        logger.info(f"Processing message: {message} for wa_id: {wa_id}")

        if not message or not wa_id:
            raise HTTPException(status_code=400, detail="Missing message or wa_id")

        # Process query and send response
        response_text, _ = await support_system.process_query(
            message,
            user_name=None
        )

        logger.info(f"Sending response to WhatsApp ID: {wa_id}")
        
        # Send the response
        await whatsapp_api.send_message(wa_id, response_text)
        
        return {
            "success": True,
            "info": "Message processed successfully",
            "response_text": response_text
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
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
