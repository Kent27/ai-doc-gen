import base64
import json
import os
import httpx
from PIL import Image  # Change this line
from io import BytesIO
from typing import Dict, Any, List, Optional
import logging
from ..models.whatsapp_models import WhatsAppWebhookRequest, WhatsAppMessage, WhatsAppContact
from ..services.openai_service import OpenAIAssistantService
from ..models.assistant_models import ChatRequest, ChatMessage, ContentItem, ImageFileContent, TextContent
from ..utils.google_sheets import check_customer_exists, update_customer, insert_customer, update_thread_id
from ..utils.logging_utils import log_whatsapp_message
import asyncio
from datetime import datetime, timedelta
from collections import OrderedDict

# Replace the existing logger with our app logger
from ..utils.app_logger import app_logger as logger

# Message deduplication cache with a max size to prevent memory leaks
class MessageCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
        
    def add(self, message_id: str) -> bool:
        """
        Add a message ID to the cache.
        Returns True if the message is new, False if it already exists.
        """
        if message_id in self.cache:
            # Update position in OrderedDict (mark as recently used)
            self.cache.move_to_end(message_id)
            return False
            
        # Add new message ID
        self.cache[message_id] = datetime.now()
        
        # Remove oldest entries if cache exceeds max size
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            
        return True
        
    def cleanup(self, max_age_minutes=30):
        """Remove entries older than max_age_minutes"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=max_age_minutes)
        
        # Create a list of keys to remove (can't modify during iteration)
        to_remove = [
            key for key, timestamp in self.cache.items() 
            if timestamp < cutoff
        ]
        
        # Remove old entries
        for key in to_remove:
            del self.cache[key]

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

        # Initialize message cache for deduplication
        self.message_cache = MessageCache()

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
                # Log status update
                if hasattr(value.statuses[0], 'recipient_id'):
                    log_whatsapp_message(
                        phone_number=value.statuses[0].recipient_id,
                        message_type="status",
                        message_data={"status": value.statuses[0].status},
                        direction="outgoing"
                    )
                # Just acknowledge status updates without processing
                return {"status": "success", "message": "Status update received"}

            # Continue only if it's a message
            if not hasattr(value, 'messages') or not value.messages:
                return {"status": "success", "message": "No messages to process"}

            messages = [WhatsAppMessage.model_validate(msg) for msg in value.messages]
            contact = WhatsAppContact.model_validate(value.contacts[0])
            
            # Check for duplicate messages to prevent double processing
            # Use the first message's ID as the key for deduplication
            message_id = messages[0].id
            if not self.message_cache.add(message_id):
                logger.info(f"Skipping duplicate message: {message_id}")
                return {"status": "success", "message": "Duplicate message skipped"}
            # Periodically clean up old message IDs
            if datetime.now().minute % 5 == 0:  # Clean up every 5 minutes
                self.message_cache.cleanup()
            
            # Log each incoming message
            for message in messages:
                log_data = {
                    "message_id": message.id,
                    "timestamp": message.timestamp,
                    "contact_name": contact.profile.name,
                }
                
                if message.type == "text" and hasattr(message, 'text'):
                    log_data["text"] = message.text.body
                elif message.type == "image" and hasattr(message, 'image'):
                    log_data["image_id"] = message.image.id
                    if hasattr(message.image, 'caption') and message.image.caption:
                        log_data["caption"] = message.image.caption
                
                log_whatsapp_message(
                    phone_number=message.from_,
                    message_type=message.type,
                    message_data=log_data,
                    direction="incoming"
                )
            
            # Check if customer exists in Google Sheets - MOVED TO BEGINNING
            customer = await check_customer_exists(messages[0].from_)
            
            # Create customer if they don't exist - MOVED FROM AFTER OPENAI CALL
            if not customer:
                logger.info(f"Customer Does Not Exist - Creating new customer record for: {contact.profile.name} ({messages[0].from_})")
                # For new customers, we need to insert the full record with a temporary thread_id
                # We'll update the thread_id after the OpenAI call
                customer_data = {
                    'phone': messages[0].from_,
                    'name': contact.profile.name,
                    'thread_id': ''  # Empty thread_id will be updated after OpenAI call
                }
                await insert_customer(customer_data)
                
                # Fetch the newly created customer record
                customer = await check_customer_exists(messages[0].from_)
                if not customer:
                    logger.error(f"Failed to create customer record for {messages[0].from_}")
            
            # Check if customer is in "Live Chat" mode - if so, skip AI processing
            if customer and customer.get('chat_status') == "Live Chat":
                logger.info(f"Customer {messages[0].from_} is in Live Chat mode. Skipping AI processing.")
                log_whatsapp_message(
                    phone_number=messages[0].from_,
                    message_type="system",
                    message_data={"message": "Live Chat mode active - AI processing skipped"},
                    direction="system"
                )
                return {"status": "success", "message": "Live Chat mode active - AI processing skipped"}
            
            # Process all messages
            content_items: List[Dict] = []
            thread_id = customer.get('thread_id') if customer else None
            
            # Add customer information as context at the beginning
            customer_context = f"Customer: {contact.profile.name}, Phone: {messages[0].from_}"
            content_items.append({
                "type": "text",
                "text": customer_context
            })
            
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
                        analysis_instruction = f"Mohon analisa gambar invoice ini dan ekstrak nomor invoice dan total pembayarannya."
                        content_items.append({
                            "type": "text",
                            "text": analysis_instruction
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

            # Get AI response with all message contents and metadata
            chat_response = await self.assistant_service.chat(ChatRequest(
                assistant_id=os.getenv("WHATSAPP_ASSISTANT_ID"),
                thread_id=thread_id,
                messages=[ChatMessage(
                    role="user",
                    content=content_items  # Send content_items directly
                )]
            ))
            
            # Update thread_id if needed
            if customer and thread_id != chat_response.thread_id:
                logger.info(f"Updating thread_id for customer {customer['phone']} from {thread_id} to {chat_response.thread_id}")
                await update_thread_id(customer, chat_response.thread_id)
            
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
                        
                        # Log outgoing message before sending
                        log_whatsapp_message(
                            phone_number=messages[0].from_,
                            message_type="text",
                            message_data={"text": response_text},
                            direction="outgoing"
                        )
                        
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
            
            # Log the error with the phone number if available
            if 'messages' in locals() and messages and hasattr(messages[0], 'from_'):
                log_whatsapp_message(
                    phone_number=messages[0].from_,
                    message_type="error",
                    message_data={"error": str(e)},
                    direction="system"
                )
            
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
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_to,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": message
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response_data = response.json()
                
                # Log the API response
                log_whatsapp_message(
                    phone_number=to,
                    message_type="api_response",
                    message_data=response_data,
                    direction="system"
                )
                
                if response.status_code != 200:
                    logger.error(f"Error sending message: {response.text}")
                    return {"status": "error", "message": response.text}
                
                return {"status": "success", "data": response_data}
                
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            
            # Log the error
            log_whatsapp_message(
                phone_number=to,
                message_type="error",
                message_data={"error": str(e)},
                direction="system"
            )
            
            return {"status": "error", "message": str(e)}