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

async def _check_active_ticket(wa_id: str) -> bool:
    """Check if there's an active (pending/assigned) ticket for this wa_id"""
    client = mongodb_service._get_client()
    db = client['yom-production']
    collection = db['queries']
    
    # Look for any unresolved tickets (status pending or assigned)
    ticket = collection.find_one({
        'wa_id': wa_id,
        'status': {'$in': ['pending', 'assigned']},
        'resolved_at': None
    })
    
    return ticket is not None


@app.post("/webhook", response_model=MessageResponse)
async def webhook(request: Request):
    try:
        body = await request.json()
        
        # Extract message data
        if 'data' in body:
            message = body['data'].get('message', '')
            wa_id = body['data'].get('wa_id', '')
            wam_id = body['data'].get('wam_id', '')
        else:
            message = body.get('message', '')
            wa_id = body.get('wa_id', '')
            wam_id = body.get('wam_id', '')

        if not message or not wa_id:
            raise HTTPException(status_code=400, detail="Missing message or wa_id")

        # Check for duplicate message
        if wam_id and wam_id in processed_message_ids:
            return {
                "success": True,
                "info": "Duplicate message, ignoring repeated webhook."
            }
        processed_message_ids.add(wam_id)

        # Check if there's an active ticket
        has_active_ticket = await _check_active_ticket(wa_id)
        if has_active_ticket:
            # Just store the message in the ticket and don't respond
            logger.info(f"Active ticket found for {wa_id}, storing message only")
            collection = mongodb_service._get_client()['yom-production']['queries']
            collection.update_one(
                {
                    'wa_id': wa_id,
                    'status': {'$in': ['pending', 'assigned']},
                    'resolved_at': None
                },
                {
                    '$push': {
                        'messages': {
                            'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                            'content': message,
                            'sender': 'customer',
                            'message_id': f"msg_{ObjectId()}"
                        }
                    }
                }
            )
            return {
                "success": True,
                "info": "Message added to existing ticket",
                "handoff_active": True
            }

        # If no active ticket, process normally
        logger.info(f"About to process query: {message} for wa_id: {wa_id}")
        response_text, needs_handoff = await support_system.process_query(
            message,
            wa_id=wa_id,
            user_name=None
        )
        
        logger.info(f"Generated response: {response_text}")
        logger.info(f"Handoff needed: {needs_handoff}")
        
        # Send response
        await whatsapp_api.send_message(wa_id, response_text)
        
        return {
            "success": True,
            "info": "Message processed successfully",
            "response_text": response_text,
            "handoff_initiated": needs_handoff
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Internal server error: {str(e)}"}

@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    request: Request
):
    """Resolve a ticket and return conversation to bot flow"""
    try:
        body = await request.json()
        final_message = body.get('final_message', 'Gracias por tu paciencia. ¿Hay algo más en lo que pueda ayudarte?')
        agent_id = body.get('agent_id')

        if not agent_id:
            raise HTTPException(status_code=400, detail="Agent ID is required")

        collection = mongodb_service._get_client()['yom-production']['queries']
        
        # Get ticket first to verify it exists and get wa_id
        ticket = collection.find_one({'_id': ObjectId(ticket_id)})
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        # Verify agent is assigned to this ticket
        if ticket.get('assigned_to') != agent_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to resolve this ticket"
            )

        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Update ticket status and add final message
        result = collection.update_one(
            {'_id': ObjectId(ticket_id)},
            {
                '$set': {
                    'status': 'resolved',
                    'resolved_at': now
                },
                '$push': {
                    'messages': {
                        'timestamp': now,
                        'content': final_message,
                        'sender': 'agent',
                        'message_id': f"msg_{ObjectId()}"
                    }
                }
            }
        )
        
        if result.modified_count > 0:
            # Send final message to customer via WhatsApp
            await whatsapp_api.send_message(ticket['wa_id'], final_message)
            
            return {
                "success": True,
                "message": "Ticket resolved and conversation returned to bot flow"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update ticket")

    except Exception as e:
        logger.error(f"Error resolving ticket: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
