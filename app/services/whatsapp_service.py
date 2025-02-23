import base64
import json
import os
import httpx
from PIL import Image  # Change this line
from io import BytesIO
from typing import Dict, Any, List
import logging
from ..models.whatsapp_models import WhatsAppWebhookRequest, WhatsAppMessage, WhatsAppContact
from ..services.openai_service import OpenAIAssistantService
from ..models.assistant_models import ChatRequest, ChatMessage, ContentItem, ImageFileContent, TextContent
from ..utils.google_sheets import check_customer_exists, update_customer, insert_customer
import asyncio

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
        
        try:
            # Create file object from bytes
            files = {
                'file': (filename, image_data, 'image/jpeg'),
                'purpose': (None, 'vision')
            }
            
            async with httpx.AsyncClient() as client:
                # Upload file
                response = await client.post(
                    url, 
                    headers=self.openai_headers,
                    files=files
                )
                
                if response.status_code != 200:
                    raise ValueError(f"Failed to upload file: {response.text}")
                
                file_data = response.json()
                
                # Verify file status
                file_id = file_data.get('id')
                if not file_id:
                    raise ValueError("No file ID in response")
                
                # Wait for file to be processed
                max_retries = 3
                retry_delay = 1  # seconds
                
                for _ in range(max_retries):
                    status_response = await client.get(
                        f"{url}/{file_id}",
                        headers=self.openai_headers
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get('status') == 'processed':
                            logger.info(f"File {filename} uploaded and processed successfully")
                            return file_data
                    
                    await asyncio.sleep(retry_delay)
                
                raise ValueError("File upload verification timed out")
                
        except Exception as e:
            logger.error(f"Error uploading file to OpenAI: {str(e)}")
            raise

    async def process_webhook(self, request: WhatsAppWebhookRequest) -> Dict[str, Any]:
        try:
            entry = request.entry[0]
            change = entry.changes[0]
            value = change.value

            # Check if this is a status update and the value is not None
            if hasattr(value, 'statuses') and value.statuses is not None:
                # Just acknowledge status updates without processing
                return {"status": "success", "message": "Status update received"}

            # Continue only if it's a message
            if not hasattr(value, 'messages') or not value.messages:
                return {"status": "success", "message": "No messages to process"}

            messages = [WhatsAppMessage.model_validate(msg) for msg in value.messages]
            contact = WhatsAppContact.model_validate(value.contacts[0])
            
            # Process all messages
            content_items: List[Dict] = []
            thread_id = None
            
            for message in messages:
                if message.type == "text":
                    content_items.append({
                        "type": "text",
                        "text": message.text.body
                    })
                elif message.type == "image":
                    try:
                        # Download and optimize image
                        image_data = await self._download_media(message.image.id)
                        
                        # Upload to OpenAI and wait for processing
                        file_response = await self.upload_file(
                            image_data,
                            f"whatsapp_image_{message.image.id}.jpg"
                        )
                        
                        if not file_response or 'id' not in file_response:
                            raise ValueError("Failed to get valid file response from OpenAI")
                            
                        logger.info(f"File uploaded successfully: {file_response['id']}")
                        
                        # Create image content dictionary
                        content_items.append({
                            "type": "image_file",
                            "image_file": {
                                "file_id": file_response["id"],
                                "detail": "high"
                            }
                        })
                        
                        # Add analysis instruction as text content
                        content_items.append({
                            "type": "text",
                            "text": f"Mohon analisa gambar invoice ini dan ekstrak nomor invoice dan total pembayarannya. Pelanggan: {contact.profile.name}, Nomor Telepon: {messages[0].from_}"
                        })
                        
                        if message.image.caption:
                            content_items.append({
                                "type": "text",
                                "text": "Caption: " + message.image.caption
                            })
                            
                    except Exception as e:
                        logger.error(f"Error processing image: {str(e)}")
                        await self.send_message(
                            to=messages[0].from_,
                            message="Maaf, terjadi kesalahan saat memproses gambar. Mohon coba lagi."
                        )
                        return {"status": "error", "message": str(e)}

            customer = await check_customer_exists(messages[0].from_)
            thread_id = customer.get('thread_id') if customer else None

            # Get AI response with all message contents and metadata
            chat_response = await self.assistant_service.chat(ChatRequest(
                assistant_id=os.getenv("WHATSAPP_ASSISTANT_ID"),
                thread_id=thread_id,
                messages=[ChatMessage(
                    role="user",
                    content=content_items  # Send content_items directly
                )]
            ))

            # Update customer data
            customer_data = {
                'phone': messages[0].from_,
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
                    # Handle the content directly as a string
                    response_text = assistant_message.content
                    
                    if response_text:
                        logger.info(f"Sending response to {messages[0].from_}: {response_text}")
                        await self.send_message(
                            to=messages[0].from_,
                            message=response_text
                        )
                    else:
                        logger.error("No text content found in assistant response")
                else:
                    logger.error("No assistant message or content found")
            else:
                logger.error("No messages in chat response")
            
            return {"status": "success"}
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {"status": "error", "message": str(e)}

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