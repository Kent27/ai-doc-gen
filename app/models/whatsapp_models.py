from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from ..models.assistant_models import ChatMessage

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
    id: str
    timestamp: str
    type: str
    text: Optional[WhatsAppTextMessage] = None
    image: Optional[WhatsAppImageMessage] = None
    
    model_config = {
        "populate_by_name": True
    }

class WhatsAppStatus(BaseModel):
    id: str
    status: str
    timestamp: str
    recipient_id: str

class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: dict
    contacts: Optional[List[dict]] = None
    messages: Optional[List[dict]] = None
    statuses: Optional[List[WhatsAppStatus]] = None

    def model_post_init(self, __context) -> None:
        if self.contacts:
            self.contacts = [
                WhatsAppContact.model_validate(contact) 
                for contact in self.contacts
            ]
        if self.messages:
            self.messages = [
                WhatsAppMessage.model_validate(message) 
                for message in self.messages
            ]

class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str

class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]

class WhatsAppWebhookRequest(BaseModel):
    object: str
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
