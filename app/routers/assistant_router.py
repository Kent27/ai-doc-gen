from fastapi import APIRouter, HTTPException, Depends
from ..models.assistant_models import AssistantConfig, AssistantResponse, Action, RunStatus, ThreadMessages, ChatRequest, ChatResponse, AssistantUpdateRequest
from ..services.openai_service import OpenAIAssistantService
from ..services.action_service import ActionService
from typing import Dict
from functools import lru_cache
from ..models.manychat_models import ManyChatRequest, ManyChatResponse

router = APIRouter(prefix="/assistant", tags=["assistant"])

@lru_cache()
def get_assistant_service():
    return OpenAIAssistantService()

@lru_cache()
def get_action_service():
    return ActionService()

@router.post("/create", response_model=AssistantResponse)
async def create_assistant(
    config: AssistantConfig,
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service),
    action_service: ActionService = Depends(get_action_service)
):
    if config.actions:
        config.tools = action_service.convert_to_openai_tools(config.actions)
    response = await assistant_service.create_assistant(config)
    if response.status == "error":
        raise HTTPException(status_code=400, detail=response.message)
    return response

@router.post("/thread", response_model=AssistantResponse)
async def create_thread(
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service)
):
    response = await assistant_service.create_thread()
    if response.status == "error":
        raise HTTPException(status_code=400, detail=response.message)
    return response

@router.post("/message/{thread_id}", response_model=AssistantResponse)
async def add_message(
    thread_id: str, 
    content: Dict[str, str],
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service)
):
    response = await assistant_service.add_message(thread_id, content["message"])
    if response.status == "error":
        raise HTTPException(status_code=400, detail=response.message)
    return response

@router.post("/run/{assistant_id}/{thread_id}", response_model=AssistantResponse)
async def run_assistant(
    assistant_id: str, 
    thread_id: str,
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service)
):
    response = await assistant_service.run_assistant(assistant_id, thread_id)
    if response.status == "error":
        raise HTTPException(status_code=400, detail=response.message)
    return response

@router.get("/run/{thread_id}/{run_id}/status", response_model=RunStatus)
async def get_run_status(
    thread_id: str,
    run_id: str,
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service)
):
    return await assistant_service.get_run_status(thread_id, run_id)

@router.get("/run/{thread_id}/{run_id}/wait", response_model=RunStatus)
async def wait_for_completion(
    thread_id: str,
    run_id: str,
    timeout: int = 300,
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service)
):
    return await assistant_service.wait_for_completion(thread_id, run_id, timeout)

@router.post("/run/{thread_id}/{run_id}/expire", response_model=RunStatus)
async def expire_run(
    thread_id: str,
    run_id: str,
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service)
):
    """Update a run status to expired"""
    try:
        return await assistant_service.expire_run(thread_id, run_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/messages/{thread_id}", response_model=ThreadMessages)
async def get_thread_messages(
    thread_id: str,
    limit: int = 10,
    order: str = "desc",
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service)
):
    return await assistant_service.get_messages(thread_id, limit, order)

@router.post("/actions/register", response_model=Dict[str, bool])
async def register_action(
    action: Action,
    action_service: ActionService = Depends(get_action_service)
):
    success = action_service.register_action(action)
    return {"success": success}

@router.get("/actions", response_model=Dict[str, Action])
async def list_actions(
    action_service: ActionService = Depends(get_action_service)
):
    return action_service.list_actions()

# Simplified chat endpoint
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    assistant_service: OpenAIAssistantService = Depends(get_assistant_service)
):
    try:
        return await assistant_service.chat(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/assistants/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(assistant_id: str, update_data: AssistantUpdateRequest):
    """Update an existing assistant"""
    try:
        assistant_service = OpenAIAssistantService()
        updated_assistant = await assistant_service.update_assistant(assistant_id, update_data)
        return AssistantResponse(
            assistant_id=updated_assistant.id,
            status="updated",
            response_data=updated_assistant.model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/manychat", response_model=ManyChatResponse)
async def handle_manychat(request: ManyChatRequest):
    try:
        service = OpenAIAssistantService()
        response = await service.manychat(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
