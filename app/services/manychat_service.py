import os
import httpx
from typing import Optional, Dict, Any

class ManyChatService:
    def __init__(self):
        self.api_key = os.getenv("MANYCHAT_API_KEY")
        self.base_url = "https://api.manychat.com"

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
