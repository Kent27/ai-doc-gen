import os
from openai import OpenAI
import json
import importlib
from ..models.assistant_models import (
    AssistantConfig, AssistantResponse, ChatMessage, RunStatus, 
    ThreadMessages, ChatRequest, ChatResponse, MessageContent
)
from ..models.manychat_models import ManyChatRequest, ManyChatResponse
from .manychat_service import ManyChatService
import asyncio
from functools import partial
from typing import Optional, Dict, Any
from ..utils.google_sheets import check_customer_exists, update_customer_name, insert_customer

class OpenAIAssistantService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            self._client = OpenAI(api_key=api_key)
        return self._client

    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous OpenAI operations in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def create_assistant(self, config: AssistantConfig) -> AssistantResponse:
        try:
            assistant = await self._run_sync(
                self.client.beta.assistants.create,
                name=config.name,
                instructions=config.instructions,
                model=config.model,
                tools=config.tools or [],
                file_ids=config.file_ids or []
            )
            return AssistantResponse(
                assistant_id=assistant.id,
                status="success",
                response_data=assistant.model_dump()
            )
        except Exception as e:
            return AssistantResponse(
                assistant_id="",
                status="error",
                message=str(e)
            )

    async def create_thread(self) -> AssistantResponse:
        try:
            thread = await self._run_sync(self.client.beta.threads.create)
            return AssistantResponse(
                assistant_id="",
                thread_id=thread.id,
                status="success",
                response_data=thread.model_dump()
            )
        except Exception as e:
            return AssistantResponse(
                assistant_id="",
                status="error",
                message=str(e)
            )

    async def add_message(self, thread_id: str, content: str) -> AssistantResponse:
        try:
            message = await self._run_sync(
                self.client.beta.threads.messages.create,
                thread_id=thread_id,
                role="user",
                content=content
            )
            return AssistantResponse(
                assistant_id="",
                thread_id=thread_id,
                status="success",
                response_data=message.model_dump()
            )
        except Exception as e:
            return AssistantResponse(
                assistant_id="",
                status="error",
                message=str(e)
            )

    async def run_assistant(self, assistant_id: str, thread_id: str) -> AssistantResponse:
        try:
            run = await self._run_sync(
                self.client.beta.threads.runs.create,
                thread_id=thread_id,
                assistant_id=assistant_id
            )
            return AssistantResponse(
                assistant_id=assistant_id,
                thread_id=thread_id,
                status="success",
                response_data=run.model_dump()
            )
        except Exception as e:
            return AssistantResponse(
                assistant_id=assistant_id,
                status="error",
                message=str(e)
            )

    async def get_run_status(self, thread_id: str, run_id: str) -> RunStatus:
        try:
            run = await self._run_sync(
                self.client.beta.threads.runs.retrieve,
                thread_id=thread_id,
                run_id=run_id
            )
            return RunStatus(
                status=run.status,
                response_data=run.model_dump()
            )
        except Exception as e:
            return RunStatus(status="error", response_data={"error": str(e)})

    async def wait_for_completion(self, thread_id: str, run_id: str, timeout: int = 300) -> RunStatus:
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            run_status = await self.get_run_status(thread_id, run_id)
            if run_status.status in ["completed", "failed", "expired"]:
                return run_status
            await asyncio.sleep(1)
        return RunStatus(status="timeout")

    async def get_messages(self, thread_id: str, limit: int = 10, order: str = "desc") -> ThreadMessages:
        try:
            messages = await self._run_sync(
                self.client.beta.threads.messages.list,
                thread_id=thread_id,
                limit=limit,
                order=order
            )
            return ThreadMessages(
                messages=[
                    MessageContent(
                        role=msg.role,
                        content=[
                            {
                                "type": content.type,
                                "text": content.text.value
                            } for content in msg.content
                        ]
                    ) for msg in messages.data
                ],
                has_more=messages.has_more,
                first_id=messages.first_id,
                last_id=messages.last_id
            )
        except Exception as e:
            raise ValueError(f"Error retrieving messages: {str(e)}")

    async def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a registered function by importing and calling it dynamically."""
        try:
            # Get function details from actions.json
            with open('app/data/actions.json', 'r') as f:
                actions = json.load(f)
            
            if function_name not in actions['actions']:
                raise ValueError(f"Function {function_name} not found in registered actions")
            
            action = actions['actions'][function_name]
            module_path, func_name = action['function_path'].rsplit('.', 1)
            
            # Import the module and get the function
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            
            # Execute the function with provided arguments
            result = await func(**arguments)
            return result
        except Exception as e:
            raise ValueError(f"Error executing function {function_name}: {str(e)}")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        try:
            # Create or use existing thread
            thread_id = request.thread_id
            if not thread_id:
                thread = await self._run_sync(self.client.beta.threads.create)
                thread_id = thread.id

            # Add message
            await self._run_sync(
                self.client.beta.threads.messages.create,
                thread_id=thread_id,
                role="user",
                content=request.messages[-1].content
            )

            # Run assistant
            run = await self._run_sync(
                self.client.beta.threads.runs.create,
                thread_id=thread_id,
                assistant_id=request.assistant_id
            )

            # Wait for completion or handle function calls
            while True:
                run_status = await self._run_sync(
                    self.client.beta.threads.runs.retrieve,
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                if run_status.status == "requires_action":
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        # Execute the function
                        result = await self._execute_function(function_name, arguments)
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result)
                        })
                    
                    # Submit tool outputs back to the run
                    await self._run_sync(
                        self.client.beta.threads.runs.submit_tool_outputs,
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                    continue
                
                if run_status.status in ["completed", "failed", "expired"]:
                    break
                    
                await asyncio.sleep(1)

            # Get messages
            messages = await self._run_sync(
                self.client.beta.threads.messages.list,
                thread_id=thread_id,
                order="desc",
                limit=10
            )

            return ChatResponse(
                assistant_id=request.assistant_id,
                thread_id=thread_id,
                messages=[
                    MessageContent(
                        role=msg.role,
                        content=[
                            {
                                "type": content.type,
                                "text": content.text.value
                            } for content in msg.content
                        ]
                    ) for msg in messages.data
                ],
                status=run_status.status
            )

        except Exception as e:
            raise ValueError(f"Chat error: {str(e)}")

    async def expire_run(self, thread_id: str, run_id: str) -> RunStatus:
        """Expire a run by cancelling it and updating its status."""
        try:
            # The OpenAI client already handles async operations internally
            run = self.client.beta.threads.runs.cancel(
                thread_id=thread_id,
                run_id=run_id
            )
            return RunStatus(
                run_id=run.id,
                status="expired",
                required_action=None,
                last_error=None
            )
        except Exception as e:
            raise Exception(f"Failed to expire run: {str(e)}")

    async def _process_manychat_background(self, request: ManyChatRequest) -> None:
        """Background task to process ManyChat request"""
        try:
            manychat_service = ManyChatService()
            phone_number = request.phone_number
            customer_name = request.customer_name

            if not phone_number:
                raise ValueError("Phone number is required")

            # Check if customer exists in Google Sheets
            customer = await check_customer_exists(phone_number)
            print(f"Customer: {customer}")
            if customer:
                # Update name if different
                if customer_name and customer_name != customer.get('name'):
                    await update_customer_name(phone_number, customer_name)
            else:
                # Insert new customer
                await insert_customer(phone_number, customer_name)

            # Handle chat with OpenAI Assistant
            chat_response = await self.chat(ChatRequest(
                assistant_id=request.assistant_id,
                thread_id=request.thread_id,
                messages=[ChatMessage(
                    role=request.messages[-1].role,
                    content=json.dumps({
                        "content": request.messages[-1].content,
                        "metadata": {
                            "phone_number": phone_number,
                            "customer_name": customer_name
                        }
                    })
                )]
            ))

            # Get the assistant's response
            assistant_message = next((msg for msg in chat_response.messages if msg.role == "assistant"), None)
            if assistant_message and assistant_message.content:
                ai_response = assistant_message.content[0].text
                
                # Set custom field with the response
                if request.subscriber_id:
                    await manychat_service.set_custom_field(
                        subscriber_id=request.subscriber_id,
                        field_id=os.getenv("MANYCHAT_RESPONSE_FIELD_ID"),
                        value=ai_response
                    )

                # Trigger ManyChat flow with the response
                await manychat_service.trigger_flow(
                    subscriber_id=request.subscriber_id,
                    flow_id=os.getenv("MANYCHAT_RESPONSE_FLOW_ID"),
                    custom_fields={
                        "ai_response": ai_response
                    }
                )

        except Exception as e:
            print(f"Background task error: {str(e)}")

    async def manychat(self, request: ManyChatRequest) -> ManyChatResponse:
        """Handle ManyChat request asynchronously"""
        try:
            # Validate initial request
            if not request.subscriber_id and not request.phone_number:
                raise ValueError("Either subscriber_id or phone_number must be provided")

            # Start background processing
            asyncio.create_task(self._process_manychat_background(request))

            # Return immediate response
            return ManyChatResponse(
                assistant_id=request.assistant_id,
                subscriber_id=request.subscriber_id,
                status="processing"
            )

        except Exception as e:
            raise ValueError(f"ManyChat request error: {str(e)}")
