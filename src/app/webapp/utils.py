"""WebApp utilities"""
from functools import wraps
from fastapi import Request

def rate_limit(limit: str):
    """
    添加限流装饰器到路由
    
    Args:
        limit: 限流规则，如 "5/minute", "10/hour"
    
    Example:
        @router.post("/api/sensitive")
        @rate_limit("5/minute")
        async def sensitive_endpoint(request: Request):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取 request
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")
            
            if request and hasattr(request.app.state, "limiter"):
                # 应用限流
                await request.app.state.limiter.check_rate_limit(limit, request)
            
            return await func(*args, **kwargs)
        
        # 设置限流元数据
        wrapper.__limit__ = limit
        return wrapper
    return decorator
