import os
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import json
from src.models.schemas import MessageResponse
from src.services.support import EnhancedSupportSystem
from src.services.whatsapp import WhatsAppAPI
from src.services.mongodb import MongoDBService

import traceback  # Add this import


logger = logging.getLogger(__name__)
processed_message_ids = set()

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
    """Handle incoming WhatsApp messages with improved deduplication."""
    global processed_message_ids
    
    try:
        body = await request.json()
        logger.info("=============== NEW WEBHOOK REQUEST ===============")
        logger.info(f"Raw body: {body}")

        
        try:
            body = await request.json()
            logger.info(f"Parsed JSON body: {json.dumps(body, indent=2)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            logger.error(f"Attempted to parse: {raw_body}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Invalid JSON: {str(e)}"}
            )

        # Extract message data
        data = body.get('data', {})
        if data:  # Wasapi format
            logger.info("Processing Wasapi format message")
            message = data.get('message', '').strip()
            wa_id = data.get('wa_id', '')
            wam_id = data.get('wam_id')
            event = data.get('event')
            
            logger.info(f"Extracted data - message: {message}, wa_id: {wa_id}, wam_id: {wam_id}, event: {event}")
            
            # Skip non-message events
            if event and event != "Enviar mensaje":
                logger.info(f"Skipping event type: {event}")
                return {
                    "success": True,
                    "info": f"Skipped event type: {event}"
                }
                
            message_metadata = {
                'from_agent': data.get('from_agent', False),
                'agent_id': data.get('agent_id'),
                'timestamp': datetime.now().isoformat()
            }
        else:  # Test format
            logger.info("Processing test format message")
            message = body.get('message', '').strip()
            wa_id = body.get('wa_id', '')
            wam_id = body.get('wam_id')
            message_metadata = {'from_agent': False}
            logger.info(f"Extracted test data - message: {message}, wa_id: {wa_id}, wam_id: {wam_id}")

        if not message or not wa_id:
            error_msg = f"Missing required fields - message: '{message}', wa_id: '{wa_id}'"
            logger.error(error_msg)
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": error_msg}
            )

        # Use wam_id for deduplication if available
        if wam_id:
            dedup_key = f"{wa_id}:{wam_id}"
            logger.info(f"Using wam_id based deduplication key: {dedup_key}")
        else:
            # Fallback to content-based deduplication
            normalized_message = ' '.join(message.lower().split())
            dedup_key = f"{wa_id}:{normalized_message}"
            logger.info(f"Using content based deduplication key: {dedup_key}")

        # Check if we've already processed this message
        if dedup_key in processed_message_ids:
            logger.info(f"Duplicate message detected with key={dedup_key}, skipping.")
            return {
                "success": True,
                "info": "Duplicate message ignored"
            }

        # Add to processed messages BEFORE processing
        processed_message_ids.add(dedup_key)
        
        # Cleanup old messages (keep last 1000)
        if len(processed_message_ids) > 1000:
            temp_list = list(processed_message_ids)
            processed_message_ids.clear()
            processed_message_ids.update(temp_list[-1000:])

        logger.info(f"Processing new message with dedup_key: {dedup_key}")
        
        try:
            # Process the query
            response_text, _ = await support_system.process_query(
                query=message,
                wa_id=wa_id,
                message_metadata=message_metadata,
                user_name=None
            )
        except Exception as e:
            logger.error(f"Error in query processing: {str(e)}")
            logger.error(f"Full query processing traceback: {traceback.format_exc()}")
            raise

        # Only send response if we got one
        if response_text:
            logger.info(f"Sending response for {dedup_key}")
            try:
                await whatsapp_api.send_message(wa_id, response_text)
                logger.info(f"Successfully sent response for {dedup_key}")
            except Exception as e:
                logger.error(f"Error sending WhatsApp message: {e}")
                logger.error(f"WhatsApp API error traceback: {traceback.format_exc()}")
                raise
        else:
            logger.info(f"No response needed for {dedup_key} (likely human handling)")
        
        return {
            "success": True,
            "info": "Message processed successfully",
            "response_text": response_text
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Internal server error: {str(e)}"}
        )



@app.get("/debug/messages")
async def get_debug_info():
    """Get information about processed messages"""
    messages_list = list(processed_message_ids)
    return {
        "processed_messages_count": len(messages_list),
        "last_10_messages": messages_list[-10:] if messages_list else [],
        "explanation": "Deduplication keys format: 'wa_id:wam_id' or 'wa_id:normalized_message'"
    }

@app.post("/debug/clear-messages")
async def clear_processed_messages():
    """Clear the processed messages set"""
    global processed_message_ids
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
