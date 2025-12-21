"""Timing wrapper for event steps, cron steps, and other non-middleware handlers."""
import time

def with_timing(step_name=None):
    """
    Decorator/wrapper function to add timing to event step handlers and other handlers
    that don't support middleware.
    
    Args:
        step_name: Optional step name to display in logs. If not provided,
                   will try to extract from context or use a generic name.
    
    Returns:
        A wrapper function that measures and logs execution time.
    """
    def decorator(handler_fn):
        # Check handler signature to determine if it's an event step or cron step
        import inspect
        sig = inspect.signature(handler_fn)
        params = list(sig.parameters.keys())
        
        # Event step: handler(input_data, context)
        # Cron step: handler(context)
        if len(params) == 2 and params[0] != 'context':
            # Event step handler
            async def wrapped_event_handler(input_data, context):
                return await _execute_with_timing(
                    handler_fn, 
                    step_name, 
                    context, 
                    lambda: handler_fn(input_data, context)
                )
            return wrapped_event_handler
        else:
            # Cron step handler (or other single-arg handlers)
            async def wrapped_cron_handler(context):
                return await _execute_with_timing(
                    handler_fn,
                    step_name,
                    context,
                    lambda: handler_fn(context)
                )
            return wrapped_cron_handler
    
    return decorator


async def _execute_with_timing(handler_fn, step_name, context, execute_fn):
    """Internal helper to execute handler with timing."""
    # Use provided step name, or try to extract from context
    final_step_name = step_name
    if not final_step_name:
        final_step_name = getattr(context, 'step_name', None) or getattr(context, 'stepName', None)
    
    # Fallback to generic name if still not available
    if not final_step_name:
        # Try to get from config if available
        if hasattr(context, 'config') and context.config:
            final_step_name = context.config.get('name', 'Step')
        else:
            final_step_name = "Step"
    
    # Record start time
    start_time = time.perf_counter()
    
    try:
        # Execute the handler
        result = await execute_fn()
        
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
        
        return result
        
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
