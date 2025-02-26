from fastapi import APIRouter, HTTPException, Request, Body
from ..services.whatsapp_service import WhatsAppService
from ..services.openai_service import OpenAIAssistantService
from ..models.whatsapp_models import WhatsAppWebhookRequest, WhatsAppChatRequest
from ..utils.google_sheets import set_chat_status, check_customer_exists
from pydantic import BaseModel
import os

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
whatsapp_service = WhatsAppService()

class ChatStatusRequest(BaseModel):
    phone_number: str
    status: str

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Handle webhook verification from WhatsApp"""
    try:
        params = request.query_params
        return await whatsapp_service.verify_webhook(
            mode=params.get("hub.mode"),
            token=params.get("hub.verify_token"),
            challenge=params.get("hub.challenge")
        )
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/webhook")
async def webhook(request: WhatsAppWebhookRequest):
    """Handle incoming messages from WhatsApp"""
    return await whatsapp_service.process_webhook(request)

@router.post("/set-chat-status")
async def set_customer_chat_status(request: ChatStatusRequest):
    """
    Set the chat status for a customer
    
    When status is set to "Live Chat", AI processing will be skipped for this customer.
    """
    try:
        # Check if customer exists
        customer = await check_customer_exists(request.phone_number)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Set the chat status
        success = await set_chat_status(request.phone_number, request.status)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update chat status")
        
        return {
            "status": "success",
            "message": f"Chat status for {request.phone_number} set to '{request.status}'",
            "phone_number": request.phone_number,
            "chat_status": request.status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))