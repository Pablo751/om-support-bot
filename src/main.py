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
    try:
        body = await request.json()
        logger.info("=============== NEW WEBHOOK REQUEST ===============")
        logger.info(f"Raw body: {body}")

        # Extract message data
        data = body.get('data', {})
        if data:  # Wasapi format
            message = data.get('message', '').strip()
            wa_id = data.get('wa_id', '')
            event = data.get('event')
            # Extract message ID if available
            message_id = data.get('message_id') or data.get('id')
            timestamp = data.get('timestamp') or datetime.now().timestamp()
            
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
                'timestamp': datetime.fromtimestamp(timestamp).isoformat() if isinstance(timestamp, (int, float)) else timestamp
            }
        else:  # Test format
            message = body.get('message', '').strip()
            wa_id = body.get('wa_id', '')
            message_id = body.get('message_id', '')
            timestamp = datetime.now().timestamp()
            message_metadata = {'from_agent': False}

        if not message or not wa_id:
            error_msg = "Missing message or wa_id"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        # Create a more robust deduplication key
        if message_id:
            # If we have a message_id, use it as the primary dedup key
            dedup_key = f"{wa_id}:{message_id}"
        else:
            # Fallback to using normalized message + timestamp (rounded to nearest minute)
            normalized_message = ' '.join(message.lower().split())
            minute_timestamp = int(timestamp - (timestamp % 60))  # Round to nearest minute
            dedup_key = f"{wa_id}:{normalized_message}:{minute_timestamp}"

        logger.info(f"Using deduplication key: {dedup_key}")
        
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
        
        # Process the query
        response_text, _ = await support_system.process_query(
            query=message,
            wa_id=wa_id,
            message_metadata=message_metadata,
            user_name=None
        )

        # Only send response if we got one
        if response_text:
            logger.info(f"Sending response for {dedup_key}")
            try:
                await whatsapp_api.send_message(wa_id, response_text)
                logger.info(f"Successfully sent response for {dedup_key}")
            except Exception as e:
                logger.error(f"Error sending WhatsApp message: {e}")
                raise
        else:
            logger.info(f"No response needed for {dedup_key} (likely human handling)")
        
        return {
            "success": True,
            "info": "Message processed successfully",
            "response_text": response_text
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}

@app.get("/debug/messages")
async def get_debug_info():
    """Get information about processed messages"""
    messages_list = list(processed_message_ids)
    
    # Parse the dedup keys to provide more readable information
    parsed_messages = []
    for msg in messages_list[-10:]:
        parts = msg.split(':')
        if len(parts) >= 3:
            # Handle timestamp format
            try:
                timestamp = datetime.fromtimestamp(float(parts[-1])).isoformat()
            except:
                timestamp = parts[-1]
            parsed_messages.append({
                'wa_id': parts[0],
                'message_or_id': parts[1],
                'timestamp': timestamp
            })
        else:
            parsed_messages.append({'raw_key': msg})

    return {
        "processed_messages_count": len(messages_list),
        "last_10_messages_parsed": parsed_messages,
        "last_10_messages_raw": messages_list[-10:] if messages_list else [],
        "explanation": "Deduplication keys now include message_id or timestamp"
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
