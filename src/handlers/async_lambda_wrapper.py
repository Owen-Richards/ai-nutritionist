"""
Async Lambda Handler Wrapper
Provides async/await support for Lambda functions with proper error handling and performance optimization.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, Optional
import json

logger = logging.getLogger(__name__)


class AsyncLambdaHandler:
    """Wrapper for converting sync Lambda handlers to async with optimizations."""
    
    def __init__(self):
        self._event_loop = None
        self._performance_stats = {
            'cold_starts': 0,
            'warm_starts': 0,
            'avg_execution_time': 0,
            'total_invocations': 0
        }
    
    def get_or_create_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get existing event loop or create new one for Lambda reuse."""
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
            return loop
        except RuntimeError:
            # Create new loop if none exists or current is closed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    def async_handler(self, async_func: Callable) -> Callable:
        """Decorator to convert async function to Lambda handler."""
        
        @functools.wraps(async_func)
        def wrapper(event: Dict[str, Any], context) -> Dict[str, Any]:
            start_time = time.time()
            
            # Track cold vs warm starts
            if not hasattr(context, '_async_handler_initialized'):
                self._performance_stats['cold_starts'] += 1
                context._async_handler_initialized = True
                logger.info("Cold start detected")
            else:
                self._performance_stats['warm_starts'] += 1
            
            try:
                # Get or create event loop
                loop = self.get_or_create_event_loop()
                
                # Run async function
                result = loop.run_until_complete(async_func(event, context))
                
                # Update performance stats
                execution_time = time.time() - start_time
                self._update_performance_stats(execution_time)
                
                return result
                
            except Exception as e:
                logger.error(f"Async handler error: {e}")
                execution_time = time.time() - start_time
                self._update_performance_stats(execution_time)
                
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'X-Execution-Time': str(execution_time)
                    },
                    'body': json.dumps({
                        'error': 'Internal server error',
                        'execution_time': execution_time
                    })
                }
        
        return wrapper
    
    def _update_performance_stats(self, execution_time: float):
        """Update performance statistics."""
        self._performance_stats['total_invocations'] += 1
        total_invocations = self._performance_stats['total_invocations']
        
        # Calculate rolling average
        current_avg = self._performance_stats['avg_execution_time']
        self._performance_stats['avg_execution_time'] = (
            (current_avg * (total_invocations - 1) + execution_time) / total_invocations
        )
        
        # Log performance metrics periodically
        if total_invocations % 10 == 0:
            logger.info(f"Performance stats: {self._performance_stats}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return dict(self._performance_stats)


# Global handler instance
async_lambda = AsyncLambdaHandler()


def async_lambda_handler(func: Callable) -> Callable:
    """Decorator for creating async Lambda handlers."""
    return async_lambda.async_handler(func)


# Async utilities for Lambda handlers
class AsyncLambdaUtils:
    """Utility functions for async Lambda operations."""
    
    @staticmethod
    async def safe_aws_call(coro, max_retries: int = 3, backoff_base: float = 1.0) -> Any:
        """Make AWS API call with retries and exponential backoff."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                result = await coro
                return result
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries - 1:
                    wait_time = backoff_base * (2 ** attempt)
                    logger.warning(f"AWS call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"AWS call failed after {max_retries} attempts: {e}")
        
        raise last_exception
    
    @staticmethod
    async def parallel_aws_calls(*coros, max_concurrent: int = 5) -> list:
        """Execute multiple AWS calls in parallel with concurrency limit."""
        
        async def _execute_with_semaphore(semaphore, coro):
            async with semaphore:
                return await AsyncLambdaUtils.safe_aws_call(coro)
        
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [_execute_with_semaphore(semaphore, coro) for coro in coros]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    @staticmethod
    def create_response(
        status_code: int = 200,
        body: Any = None,
        headers: Optional[Dict[str, str]] = None,
        cors_enabled: bool = True
    ) -> Dict[str, Any]:
        """Create standardized Lambda response."""
        
        response_headers = {
            'Content-Type': 'application/json'
        }
        
        if cors_enabled:
            response_headers.update({
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
            })
        
        if headers:
            response_headers.update(headers)
        
        response_body = body
        if body is not None and not isinstance(body, str):
            response_body = json.dumps(body, default=str)
        
        return {
            'statusCode': status_code,
            'headers': response_headers,
            'body': response_body or ''
        }
    
    @staticmethod
    async def with_timeout(coro, timeout: float = 25.0):
        """Execute coroutine with timeout (Lambda has 30s max)."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {timeout}s")
            raise Exception(f"Operation timed out after {timeout}s")


# Export utilities
utils = AsyncLambdaUtils()
