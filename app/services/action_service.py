import asyncio
import httpx
from typing import Dict, Any, List, Callable
from ..models.assistant_models import Action
import json
from pathlib import Path
import os
from fastapi import HTTPException
import importlib
from functools import partial

class ActionService:
    _instance = None
    _actions_file = Path("app/data/actions.json")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ActionService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the service and create storage file if it doesn't exist."""
        self._actions_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._actions_file.exists():
            self._save_actions({})
        self._load_actions()
        self._function_registry = {}

    def _load_actions(self) -> None:
        """Load actions from JSON file."""
        try:
            with open(self._actions_file, 'r') as f:
                data = json.load(f)
                self._actions = {
                    name: Action(**action_data)
                    for name, action_data in data.get('actions', {}).items()
                }
        except json.JSONDecodeError:
            self._actions = {}
            self._save_actions(self._actions)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load actions: {str(e)}")

    def _save_actions(self, actions: Dict[str, Any]) -> None:
        """Save actions to JSON file."""
        try:
            with open(self._actions_file, 'w') as f:
                json.dump({'actions': {
                    name: action.dict()
                    for name, action in actions.items()
                }}, f, indent=4)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save actions: {str(e)}")

    def _load_function(self, function_path: str) -> Callable:
        """Dynamically load a function from a module."""
        try:
            module_path, function_name = function_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, function_name)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load function {function_path}: {str(e)}"
            )

    def register_action(self, action: Action) -> bool:
        """Register a new action with persistence."""
        try:
            # Verify local function can be loaded if specified
            if action.is_local_function:
                self._function_registry[action.name] = self._load_function(action.function_path)
            
            self._actions[action.name] = action
            self._save_actions(self._actions)
            return True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to register action: {str(e)}")

    def get_action(self, name: str) -> Action:
        """Get an action by name."""
        if name not in self._actions:
            raise HTTPException(status_code=404, detail=f"Action {name} not found")
        return self._actions.get(name)

    def list_actions(self) -> Dict[str, Action]:
        """List all registered actions."""
        return self._actions

    def delete_action(self, name: str) -> bool:
        """Delete an action by name."""
        try:
            if name in self._actions:
                del self._actions[name]
                self._function_registry.pop(name, None)  # Remove from function registry if exists
                self._save_actions(self._actions)
                return True
            return False
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete action: {str(e)}")

    def convert_to_openai_tools(self, actions: List[Action]) -> List[Dict[str, Any]]:
        tools = []
        for action in actions:
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
                                "description": param.description
                            } for param in action.parameters
                        },
                        "required": [param.name for param in action.parameters if param.required]
                    }
                }
            }
            tools.append(tool)
        return tools

    async def execute_action(self, action_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute either a remote API call or local function."""
        action = self._actions.get(action_name)
        if not action:
            raise ValueError(f"Action {action_name} not found")

        try:
            if action.is_local_function:
                # Execute local function
                func = self._function_registry.get(action_name)
                if not func:
                    # Try loading function if not in registry
                    func = self._load_function(action.function_path)
                    self._function_registry[action_name] = func
                
                # Execute function with parameters
                if asyncio.iscoroutinefunction(func):
                    result = await func(**parameters)
                else:
                    result = func(**parameters)
                return result
            else:
                # Execute remote API call
                return await self._execute_remote_action(action, parameters)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute action {action_name}: {str(e)}"
            )

    async def _execute_remote_action(self, action: Action, parameters: Dict[str, Any]) -> Any:
        """Execute a remote API call."""
        headers = action.headers or {}
        if action.auth_type and action.auth_key:
            if action.auth_type.lower() == "bearer":
                headers["Authorization"] = f"Bearer {action.auth_key}"
            else:
                headers["Authorization"] = action.auth_key

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=action.method,
                url=str(action.url),
                json=parameters,
                headers=headers
            )
            return response.json()
