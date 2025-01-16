from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class WhatsAppMessage(BaseModel):
    wa_id: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class MessageResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    info: Optional[str] = None
    response_text: Optional[str] = None

class WebhookRequest(BaseModel):
    message: str
    wa_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hola",
                "wa_id": "123456789"
            }
        }