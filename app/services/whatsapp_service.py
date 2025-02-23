import os
import httpx
from typing import Dict, Any
import logging
logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.api_version = "v22.0"
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if not all([self.phone_number_id, self.access_token]):
            raise ValueError("Missing required WhatsApp environment variables")
            
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
            "text": {"preview_url": False, "body": message}
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