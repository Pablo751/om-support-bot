import os
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from collections import defaultdict
import time
from src.models.schemas import MessageResponse
from src.services.support import EnhancedSupportSystem
from src.services.whatsapp import WhatsAppAPI
from src.services.mongodb import MongoDBService

logger = logging.getLogger(__name__)

app = FastAPI(title="YOM Support Bot", version="1.0.0")

class MessageDeduplication:
    def __init__(self, max_age_seconds=3600):  # 1 hour default
        self.processed_message_ids = set()  # For message_id based dedup
        self.recent_messages = defaultdict(list)  # For content based dedup
        self.max_age_seconds = max_age_seconds
    
    def _cleanup_old_messages(self, current_time):
        # Remove messages older than max_age_seconds
        cutoff_time = current_time - self.max_age_seconds
        for wa_id in list(self.recent_messages.keys()):
            self.recent_messages[wa_id] = [
                (msg, ts) for msg, ts in self.recent_messages[wa_id]
                if ts > cutoff_time
            ]
            if not self.recent_messages[wa_id]:
                del self.recent_messages[wa_id]
    
    def is_duplicate(self, wa_id, message, message_id=None, current_time=None):
        if current_time is None:
            current_time = time.time()
            
        # Clean up old messages first
        self._cleanup_old_messages(current_time)
        
        # If we have a message_id and it's already processed, it's a duplicate
        if message_id and message_id in self.processed_message_ids:
            return True
            
        # Check for recent identical messages from the same user
        normalized_message = ' '.join(message.lower().split())
        recent_messages = self.recent_messages[wa_id]
        
        # Check if we've seen this exact message in the last minute
        ONE_MINUTE = 60
        for msg, ts in recent_messages:
            if msg == normalized_message and (current_time - ts) < ONE_MINUTE:
                return True
                
        # Not a duplicate - add to tracking
        if message_id:
            self.processed_message_ids.add(message_id)
        self.recent_messages[wa_id].append((normalized_message, current_time))
        
        # Trim processed_message_ids if it gets too large
        if len(self.processed_message_ids) > 10000:
            self.processed_message_ids.clear()
        
        return False

    def get_debug_info(self):
        """Get debug information about current state"""
        return {
            "processed_ids_count": len(self.processed_message_ids),
            "recent_messages": {wa_id: [(msg, datetime.fromtimestamp(ts).isoformat()) 
                                      for msg, ts in msgs] 
                              for wa_id, msgs in self.recent_messages.items()}
        }

# Create the deduplication instance AFTER the class is defined
message_dedup = MessageDeduplication()

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
            message_id = data.get('message_id') or data.get('id')
            
            message_metadata = {
                'from_agent': data.get('from_agent', False),
                'agent_id': data.get('agent_id'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Skip non-message events
            if event and event != "Enviar mensaje":
                logger.info(f"Skipping event type: {event}")
                return {
                    "success": True,
                    "info": f"Skipped event type: {event}"
                }
        else:  # Test format
            message = body.get('message', '').strip()
            wa_id = body.get('wa_id', '')
            message_id = body.get('message_id', '')
            message_metadata = {'from_agent': False}

        if not message or not wa_id:
            error_msg = "Missing message or wa_id"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        # Check for duplicates using new system
        if message_dedup.is_duplicate(wa_id, message, message_id):
            logger.info(f"Duplicate message detected for wa_id={wa_id}, message_id={message_id}")
            return {
                "success": True,
                "info": "Duplicate message ignored"
            }

        # Process the query
        response_text, _ = await support_system.process_query(
            query=message,
            wa_id=wa_id,
            message_metadata=message_metadata,
            user_name=None
        )

        # Only send response if we got one
        if response_text:
            logger.info(f"Sending response for wa_id={wa_id}")
            try:
                await whatsapp_api.send_message(wa_id, response_text)
                logger.info(f"Successfully sent response for wa_id={wa_id}")
            except Exception as e:
                logger.error(f"Error sending WhatsApp message: {e}")
                raise
        else:
            logger.info(f"No response needed for wa_id={wa_id} (likely human handling)")
        
        return {
            "success": True,
            "info": "Message processed successfully",
            "response_text": response_text
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Internal server error: {str(e)}"}

@app.get("/debug/messages")
async def get_debug_info():
    """Get information about processed messages"""
    debug_info = message_dedup.get_debug_info()
    return {
        "processed_ids_count": debug_info["processed_ids_count"],
        "recent_messages": debug_info["recent_messages"],
        "explanation": "Using time-based deduplication with message IDs and content matching"
    }

@app.post("/debug/clear-messages")
async def clear_processed_messages():
    """Clear all deduplication data"""
    message_dedup.processed_message_ids.clear()
    message_dedup.recent_messages.clear()
    return {"success": True, "message": "Deduplication data cleared"}

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
