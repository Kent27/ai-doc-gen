from app.models.assistant_models import AssistantUpdateRequest
from openai import AsyncOpenAI
# ...existing code...

class AssistantService:
    # ...existing code...
    
    async def update_assistant(self, assistant_id: str, update_data: AssistantUpdateRequest):
        """Update an existing assistant with new configuration"""
        client = AsyncOpenAI()
        
        # Convert the update data to dict and remove None values
        update_dict = update_data.model_dump(exclude_none=True)
        
        # If actions are provided, convert them to OpenAI tool format
        if "actions" in update_dict:
            tools = []
            for action in update_dict["actions"]:
                tool = {
                    "type": "function",
                    "function": {
                        "name": action.name,
                        "description": action.description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                param.name: {
                                    "type": param.type,
                                    "description": param.description,
                                    **({"enum": param.enum} if param.enum else {})
                                }
                                for param in action.parameters
                            },
                            "required": [
                                param.name for param in action.parameters 
                                if param.required
                            ]
                        }
                    }
                }
                tools.append(tool)
            update_dict["tools"] = tools
            del update_dict["actions"]
        
        try:
            return await client.beta.assistants.update(
                assistant_id=assistant_id,
                **update_dict
            )
        except Exception as e:
            raise Exception(f"Failed to update assistant: {str(e)}")
