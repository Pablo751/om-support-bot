# src/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class MessageResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    info: Optional[str] = None
    response_text: Optional[str] = None

class WebhookRequest(BaseModel):
    message: str
    wa_id: str

class WasapiMessage(BaseModel):
    message: str
    wa_id: str
    wam_id: Optional[str] = None
    message_type: Optional[str] = None
    type: Optional[str] = None

class WasapiWebhookRequest(BaseModel):
    data: WasapiMessage
