import os
import httpx
from typing import Optional, Dict, Any

class WhatsAppService:
    def __init__(self):
        self.api_version = "v18.0"
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
    async def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a text message to a WhatsApp number"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        print("Sending message", data)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code != 200:
                raise ValueError(f"WhatsApp API error: {response.text}")
            print("Response", response.json())
            return response.json()

    def verify_webhook(self, mode: str, token: str, challenge: str) -> bool:
        """Verify webhook subscription"""
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        return mode == "subscribe" and token == verify_token
