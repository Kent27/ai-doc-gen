from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from ..models.assistant_models import MessageContent, ChatMessage

class WhatsAppProfile(BaseModel):
    name: Optional[str] = None

class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile

class WhatsAppTextMessage(BaseModel):
    body: str

class WhatsAppImageMessage(BaseModel):
    id: str
    mime_type: str
    sha256: str
    caption: Optional[str] = None

class WhatsAppMessage(BaseModel):
    from_: str = Field(alias="from")
    type: str
    text: Optional[WhatsAppTextMessage] = None
    image: Optional[WhatsAppImageMessage] = None
    
    model_config = {
        "populate_by_name": True
    }

class WhatsAppValue(BaseModel):
    messages: List[WhatsAppMessage]
    contacts: List[WhatsAppContact]

class WhatsAppChange(BaseModel):
    value: WhatsAppValue

class WhatsAppEntry(BaseModel):
    changes: List[WhatsAppChange]

class WhatsAppWebhookRequest(BaseModel):
    entry: List[WhatsAppEntry]

class WhatsAppChatRequest(BaseModel):
    assistant_id: str
    thread_id: Optional[str] = None
    message: str
    phone_number: str
    customer_name: Optional[str] = None

class WhatsAppResponse(BaseModel):
    assistant_id: str
    thread_id: Optional[str] = None
    status: str
