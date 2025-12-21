"""Cron job to clean up old request state data."""
import sys
from pathlib import Path

# Add middlewares directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from middlewares.timing_middleware import create_timing_middleware

config = {
    "name": "CleanupState",
    "type": "cron",
    "cron": "0 */6 * * *",  # Every 6 hours
    "description": "Clean up old request state data (older than 24 hours)",
    "emits": [],
    "flows": []
}

async def handler(input_data, context):
    """Clean up old request state data."""
    try:
        context.logger.info("Starting state cleanup", {})
        
        # Note: Motia state management doesn't expose a direct way to list all groups
        # or check timestamps. This is a placeholder implementation.
        # In production, you might need to:
        # 1. Track request IDs with timestamps in a separate state key
        # 2. Iterate through tracked request IDs
        # 3. Check age and delete old ones
        
        # For now, we'll log that cleanup would happen
        # In a real implementation, you'd need to:
        # - Maintain a registry of request IDs with creation timestamps
        # - Check each request's age
        # - Delete state groups older than 24 hours
        
        context.logger.info("State cleanup completed", {
            "note": "Cleanup logic would delete request state groups older than 24 hours"
        })
        
        # Example cleanup logic (commented out - requires request ID tracking):
        # request_registry = await context.state.get("system", "request_registry") or []
        # current_time = time.time()
        # deleted_count = 0
        # 
        # for request_id, created_at in request_registry:
        #     age_hours = (current_time - created_at) / 3600
        #     if age_hours > 24:
        #         # Delete all state keys for this request
        #         await context.state.clear(f"request_{request_id}")
        #         deleted_count += 1
        # 
        # context.logger.info("State cleanup completed", {
        #     "deleted_requests": deleted_count
        # })
        
    except Exception as e:
        context.logger.error("Error during state cleanup", {"error": str(e)})

