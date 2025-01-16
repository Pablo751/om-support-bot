# In src/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict

class WasapiMessage(BaseModel):
    message: str
    wa_id: str
    wam_id: Optional[str] = None
    message_type: Optional[str] = None
    type: Optional[str] = None

class WasapiWebhookRequest(BaseModel):
    data: WasapiMessage

# In src/main.py
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
