import httpx
import json
from typing import Dict, Any
from ..models.api_models import APIConfig, APIResponse

async def analyze_structure(data: Any) -> Dict[str, Any]:
    """Analyze the structure of the response data"""
    if isinstance(data, dict):
        return {k: type(v).__name__ for k, v in data.items()}
    elif isinstance(data, list):
        return {"array": type(data[0]).__name__ if data else "empty"} 
    else:
        return {"value": type(data).__name__}

async def make_api_request(config: APIConfig) -> APIResponse:
    """
    Make an API request based on the provided configuration
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=config.method,
                url=str(config.url),
                headers=config.headers,
                params=config.params,
                json=config.body,
                timeout=config.timeout
            )
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = response.text

            structure = await analyze_structure(data)
            
            return APIResponse(
                status_code=response.status_code,
                success=response.is_success,
                data=data,
                structure=structure,
                error=None if response.is_success else f"HTTP {response.status_code}"
            )

    except Exception as e:
        return APIResponse(
            status_code=500,
            success=False,
            data=None,
            structure={},
            error=str(e)
        )
