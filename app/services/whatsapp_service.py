import base64
import json
import os
import httpx
from PIL import Image  # Change this line
from io import BytesIO
from typing import Dict, Any, List
import logging
from ..models.whatsapp_models import WhatsAppWebhookRequest
from ..services.openai_service import OpenAIAssistantService
from ..models.assistant_models import ChatRequest, ChatMessage, ContentItem, ImageFileContent, TextContent
from ..utils.google_sheets import check_customer_exists, update_customer, insert_customer

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.api_version = "v22.0"
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.assistant_service = OpenAIAssistantService()
        self.openai_headers = {
            "OpenAI-Beta": "assistants=v2",
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
        }
        self.base_openai_url = "https://api.openai.com/v1"

        if not all([self.phone_number_id, self.access_token]):
            raise ValueError("Missing required WhatsApp environment variables")
        
    async def verify_webhook(self, mode: str, token: str, challenge: str) -> int:
        """Verify WhatsApp webhook"""
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        if mode == "subscribe" and token == verify_token:
            return int(challenge)
        raise ValueError("Invalid verification token")

    async def upload_file(self, image_data: bytes, filename: str) -> dict:
        """Upload file to OpenAI for vision processing"""
        url = f"{self.base_openai_url}/files"
        
        # Create file object from bytes
        files = {
            'file': (filename, image_data, 'image/jpeg'),
            'purpose': (None, 'vision')
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                headers=self.openai_headers, 
                files=files
            )
            response.raise_for_status()
            return response.json()
            
    async def process_webhook(self, request: WhatsAppWebhookRequest) -> Dict[str, Any]:
        try:
            entry = request.entry[0]
            change = entry.changes[0]
            value = change.value
            messages = value.messages
            contact = value.contacts[0]
            
            # Process all messages
            content_items: List[Dict] = []
            thread_id = None
            
            for message in messages:
                if message.type == "text":
                    # Create text content dictionary
                    content_items.append({
                        "type": "text",
                        "text": message.text.body
                    })
                elif message.type == "image":
                    # Download and optimize image
                    image_data = await self._download_media(message.image.id)
                    optimized_image = await self._optimize_image(image_data)
                    
                    # Upload to OpenAI
                    file_response = await self.upload_file(
                        optimized_image,
                        f"whatsapp_image_{message.image.id}.jpg"
                    )
                    
                    # Create image content dictionary
                    content_items.append({
                        "type": "image_file",
                        "image_file": {
                            "file_id": file_response["id"],
                            "detail": "high"
                        }
                    })
                    
                    if message.image.caption:
                        content_items.append({
                            "type": "text",
                            "text": message.image.caption
                        })

            customer = await check_customer_exists(message.from_)
            thread_id = customer.get('thread_id') if customer else None

            # Get AI response with all message contents and metadata
            chat_response = await self.assistant_service.chat(ChatRequest(
                assistant_id=os.getenv("WHATSAPP_ASSISTANT_ID"),
                thread_id=thread_id,
                messages=[ChatMessage(
                    role="user",
                    content=[{
                        "type": "text",
                        "text": json.dumps({
                            "content": content_items,
                            "metadata": {
                                "phone_number": message.from_,
                                "customer_name": contact.profile.name
                            }
                        })
                    }]
                )]
            ))
            
            # Update customer data
            customer_data = {
                'phone': message.from_,
                'name': contact.profile.name,
                'thread_id': chat_response.thread_id
            }
            
            if customer:
                await update_customer(customer, customer_data)
            else:
                await insert_customer(customer_data)
            
            # Send response
            if chat_response.messages:
                assistant_message = next(
                    (msg for msg in chat_response.messages if msg.role == "assistant"),
                    None
                )
                if assistant_message and assistant_message.content:
                    response_text = assistant_message.content[0].text
                    await self.send_message(
                        to=message.from_,
                        message=response_text
                    )
            
            return {"status": "success"}
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {"status": "error", "message": str(e)}
        
    async def _optimize_image(self, image_data: bytes, max_size: int = 800) -> bytes:
        """Optimize image size while maintaining quality"""
        image = Image.open(BytesIO(image_data))
        
        # Calculate new dimensions while maintaining aspect ratio
        ratio = min(max_size / image.width, max_size / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        
        # Resize and compress
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        return output.getvalue()

    async def _download_media(self, media_id: str) -> bytes:
        """Download media from WhatsApp"""
        # First get media URL
        url = f"{self.base_url}/{media_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            # Get media URL
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to get media URL: {response.text}")
            
            media_url = response.json().get("url")
            
            # Download media
            media_response = await client.get(media_url, headers=headers)
            if media_response.status_code != 200:
                raise ValueError("Failed to download media")
                
            return media_response.content
            
    async def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a text message to a WhatsApp number"""
        # Format phone number
        formatted_to = to.replace("+", "").strip()
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_to,
            "type": "text",
            "text": {"preview_url": True, "body": message}
        }
        
        logger.info(f"Sending WhatsApp message to {formatted_to}")
        logger.debug(f"Request data: {data}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                response_data = response.json()
                logger.debug(f"WhatsApp API response: {response_data}")
                
                if response.status_code != 200:
                    logger.error(f"WhatsApp API error: {response.text}")
                    raise ValueError(f"WhatsApp API error: {response.text}")
                    
                return response_data
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            raise