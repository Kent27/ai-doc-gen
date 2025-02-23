from fastapi import APIRouter, HTTPException, Request
from ..services.whatsapp_service import WhatsAppService
from ..services.openai_service import OpenAIAssistantService
from ..models.whatsapp_models import WhatsAppWebhookRequest, WhatsAppChatRequest
import os

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
whatsapp_service = WhatsAppService()

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