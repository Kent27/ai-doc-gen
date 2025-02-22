from pydantic import BaseModel
from typing import Optional, List
from ..models.assistant_models import ChatMessage

class ManyChatRequest(BaseModel):
    assistant_id: str
    thread_id: Optional[str] = None
    messages: List[ChatMessage]
    subscriber_id: Optional[str] = None
    phone_number: Optional[str] = None
    customer_name: Optional[str] = None  # Add customer name field
    
class ManyChatResponse(BaseModel):
    assistant_id: str
    subscriber_id: Optional[str] = None
    thread_id: Optional[str] = None  # Add thread_id to response
    status: str  # Can be "success", "error", "processing"
