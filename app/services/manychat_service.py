import os
import httpx
from typing import Optional, Dict, Any

class ManyChatService:
    def __init__(self):
        self.api_key = os.getenv("MANYCHAT_API_KEY")
        self.base_url = "https://api.manychat.com"
        
    async def create_subscriber(self, phone_number: str) -> Dict[str, Any]:
        """Create a new subscriber in ManyChat"""
        if not phone_number:
            raise ValueError("Phone number is required")
            
        # Simple phone number format validation
        phone_number = phone_number.strip().replace(" ", "")
        if not phone_number.startswith("+") and not phone_number.startswith("00"):
            phone_number = "+" + phone_number

        url = f"{self.base_url}/fb/subscriber/createByPhone"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "phone": phone_number
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response_data = response.json()
            
            if response.status_code != 200:
                error_msg = response_data.get('message') or "Unknown error"
                raise ValueError(f"ManyChat API error: {error_msg}")
                
            if not response_data.get('data', {}).get('id'):
                raise ValueError("Invalid response from ManyChat: missing subscriber ID")
                
            return response_data

    async def set_custom_field(self, subscriber_id: str, field_id: str, value: str) -> Dict[str, Any]:
        """Set a custom field value for a subscriber"""
        url = f"{self.base_url}/fb/subscriber/setCustomField"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "subscriber_id": subscriber_id,
            "field_id": field_id,
            "field_value": value
        }
            
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code != 200:
                raise ValueError(f"ManyChat API error: {response.json().get('message')}")
            return response.json()

    async def trigger_flow(self, subscriber_id: str, flow_id: str, custom_fields: Optional[Dict] = None) -> Dict[str, Any]:
        """Trigger a flow for a subscriber"""
        url = f"{self.base_url}/fb/sending/sendFlow"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "subscriber_id": subscriber_id,
            "flow_ns": flow_id,
        }
        if custom_fields:
            data["custom_fields"] = custom_fields
            
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code != 200:
                raise ValueError(f"ManyChat API error: {response.json().get('message')}")
            return response.json()
