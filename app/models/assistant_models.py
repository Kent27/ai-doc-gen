from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, Union, Literal, Callable

class ActionParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = False
    enum: Optional[List[str]] = None

class ActionConfig(BaseModel):
    type: Literal["function"]
    function: Dict[str, Any]

class Action(BaseModel):
    name: str
    description: str
    url: Optional[HttpUrl] = None
    method: Optional[str] = "POST"
    headers: Optional[Dict[str, str]] = None
    parameters: List[ActionParameter]
    auth_type: Optional[str] = None
    auth_key: Optional[str] = None
    function_path: Optional[str] = None  # Format: "module_name.function_name"
    
    class Config:
        arbitrary_types_allowed = True
        
    @property
    def is_local_function(self) -> bool:
        return self.function_path is not None and self.url is None

class AssistantConfig(BaseModel):
    name: str
    instructions: str
    model: str = "gpt-4-1106-preview"
    tools: Optional[List[Union[ActionConfig, Dict[str, Any]]]] = None
    actions: Optional[List[Action]] = None
    file_ids: Optional[List[str]] = None

class AssistantUpdateRequest(BaseModel):
    name: Optional[str] = None
    instructions: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[Union[ActionConfig, Dict[str, Any]]]] = None
    actions: Optional[List[Action]] = None
    file_ids: Optional[List[str]] = None

class AssistantResponse(BaseModel):
    assistant_id: str
    thread_id: Optional[str] = None
    message: Optional[str] = None
    status: str
    response_data: Optional[Dict[str, Any]] = None

class RunStatus(BaseModel):
    status: str
    response_data: Optional[Dict[str, Any]] = None

class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str

class ImageFileContent(BaseModel):
    type: Literal["image_file"] = "image_file"
    image_file: Dict[str, str]

ContentItem = Union[TextContent, ImageFileContent]

class ChatMessage(BaseModel):
    role: str
    content: List[ContentItem]

class ThreadMessages(BaseModel):
    messages: List[ChatMessage]
    has_more: bool
    first_id: Optional[str] = None
    last_id: Optional[str] = None
class ChatRequest(BaseModel):
    assistant_id: str
    messages: List[ChatMessage]
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    assistant_id: str
    thread_id: str
    messages: List[ChatMessage]
    status: str
