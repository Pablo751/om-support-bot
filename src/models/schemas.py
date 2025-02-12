from pydantic import BaseModel
from typing import Optional

class MessageResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    info: Optional[str] = None
    response_text: Optional[str] = None
