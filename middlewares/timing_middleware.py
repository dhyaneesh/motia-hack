"""Timing middleware to measure and log step execution time."""
import time

def create_timing_middleware(step_name=None):
    """
    Factory function to create a timing middleware with a specific step name.
    
    Args:
        step_name: Optional step name to display in logs. If not provided,
                   will try to extract from context or use a generic name.
    
    Returns:
        A middleware function that measures and logs execution time.
    """
    async def timing_middleware(req, context, next_fn):
        """
        Middleware that measures and logs the execution time of each step.
        
        Logs timing information to the console in a clear format:
        - Step name
        - Execution duration in milliseconds
        - Duration in seconds (for longer operations)
        """
        # Use provided step name, or try to extract from context
        final_step_name = step_name
        if not final_step_name:
            final_step_name = getattr(context, 'step_name', None) or getattr(context, 'stepName', None)
        
        # Fallback to generic name if still not available
        if not final_step_name:
            path_params = req.get('pathParams', {})
            if path_params:
                final_step_name = f"API Step (params: {', '.join(path_params.keys())})"
            else:
                final_step_name = "API Step"
        
        # Record start time
        start_time = time.perf_counter()
        
        try:
            # Execute the next middleware/handler
            response = await next_fn()
            
            # Record end time
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            duration_s = end_time - start_time
            
            # Format duration for display
            if duration_s >= 1.0:
                duration_str = f"{duration_s:.2f}s ({duration_ms:.0f}ms)"
            else:
                duration_str = f"{duration_ms:.2f}ms"
            
            # Log using context logger (avoids RPC interference and encoding issues)
            # Use logger.info for clear console output without breaking RPC
            context.logger.info("=" * 60)
            context.logger.info(f"STEP TIMING: {final_step_name}")
            context.logger.info(f"Duration: {duration_str}")
            context.logger.info("=" * 60)
            
            # Also log structured data for programmatic access
            context.logger.info("Step execution timing", {
                "step_name": final_step_name,
                "duration_ms": round(duration_ms, 2),
                "duration_s": round(duration_s, 3)
            })
            
            return response
            
        except Exception as e:
            # Still log timing even if there's an error
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            duration_s = end_time - start_time
            
            if duration_s >= 1.0:
                duration_str = f"{duration_s:.2f}s ({duration_ms:.0f}ms)"
            else:
                duration_str = f"{duration_ms:.2f}ms"
            
            # Log using context logger (avoids RPC interference and encoding issues)
            context.logger.error("=" * 60)
            context.logger.error(f"STEP TIMING (ERROR): {final_step_name}")
            context.logger.error(f"Duration: {duration_str}")
            context.logger.error(f"Error: {str(e)}")
            context.logger.error("=" * 60)
            
            # Also log structured data for programmatic access
            context.logger.error("Step execution timing (with error)", {
                "step_name": final_step_name,
                "duration_ms": round(duration_ms, 2),
                "duration_s": round(duration_s, 3),
                "error": str(e)
            })
            
            # Re-raise the exception so error handling works normally
            raise
    
    return timing_middleware

# Default middleware instance (for backward compatibility)
# Can be used directly, or use create_timing_middleware(step_name) for named steps
timing_middleware = create_timing_middleware()
