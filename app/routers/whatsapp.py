from fastapi import APIRouter, HTTPException, Request
from ..services.whatsapp_service import WhatsAppService
from ..services.openai_service import OpenAIAssistantService
from ..models.whatsapp_models import WhatsAppWebhookRequest, WhatsAppChatRequest
import os

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
whatsapp_service = WhatsAppService()
assistant_service = OpenAIAssistantService()

@router.get("/webhook")
async def verify_webhook(mode: str, verify_token: str, challenge: str):
    """Handle webhook verification from WhatsApp"""
    if whatsapp_service.verify_webhook(mode, verify_token, challenge):
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook")
async def webhook(request: WhatsAppWebhookRequest):
    """Handle incoming messages from WhatsApp"""
    try:
        # Get first message
        entry = request.entry[0]
        change = entry.changes[0]
        value = change.value
        message = value.messages[0]
        
        # Get contact info
        contact = value.contacts[0]
        
        # Process with Assistant API
        chat_request = WhatsAppChatRequest(
            assistant_id=os.getenv("WHATSAPP_ASSISTANT_ID"),
            message=message.text.body,
            phone_number=message.from_,
            customer_name=contact.profile.name
        )
        
        # Get response from Assistant
        response = await assistant_service.whatsapp_chat(chat_request)
        
        # Send initial response
        if response.status == "processing":
            await whatsapp_service.send_message(
                to=message.from_,
                message="Processing your request..."
            )
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}
