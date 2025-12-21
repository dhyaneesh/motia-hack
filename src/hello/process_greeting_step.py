import asyncio
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_wrapper import with_timing

# Optional: Using Pydantic for validation (remove if not using Pydantic)
try:
    from pydantic import BaseModel
    
    class GreetingInput(BaseModel):
        timestamp: str
        appName: str
        greetingPrefix: str
        requestId: str
    
    # If using Pydantic, we can generate the JSON schema
    input_schema = GreetingInput.model_json_schema()
except ImportError:
    # Without Pydantic, define JSON schema manually
    input_schema = {
        "type": "object",
        "properties": {
            "timestamp": {"type": "string"},
            "appName": {"type": "string"},
            "greetingPrefix": {"type": "string"},
            "requestId": {"type": "string"}
        },
        "required": ["timestamp", "appName", "greetingPrefix", "requestId"]
    }

config = {
    "name": "ProcessGreeting",
    "type": "event",
    "description": "Processes greeting in the background",
    "subscribes": ["process-greeting"],
    "emits": [],
    "flows": ["hello-world-flow"],
    "input": input_schema
}

@with_timing("ProcessGreeting")
async def handler(input_data, context):
    # Extract data from input
    timestamp = input_data.get("timestamp")
    app_name = input_data.get("appName")
    greeting_prefix = input_data.get("greetingPrefix")
    request_id = input_data.get("requestId")
    
    context.logger.info("Processing greeting", {
        "request_id": request_id,
        "app_name": app_name
    })
    
    greeting = f"{greeting_prefix} {app_name}!"
    
    # Store result in state (demonstrates state usage)
    # Note: The state.set method takes (groupId, key, value)
    await context.state.set("greetings", request_id, {
        "greeting": greeting,
        "processedAt": datetime.now(timezone.utc).isoformat(),
        "originalTimestamp": timestamp
    })
    
    context.logger.info("Greeting processed successfully", {
        "request_id": request_id,
        "greeting": greeting,
        "stored_in_state": True
    })
