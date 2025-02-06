from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional, Union

class APIConfig(BaseModel):
    url: HttpUrl
    method: str
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 30

class APIResponse(BaseModel):
    status_code: int
    success: bool
    data: Any
    structure: Dict[str, Any]
    error: Optional[str] = None
