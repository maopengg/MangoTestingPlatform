from fastapi import Request, HTTPException
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(f'{request.method} {request.url} - {response.status_code} - {process_time:.2f}s')
        
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 简化的认证中间件示例
        # 在实际应用中，这里会验证JWT令牌等
        
        # 将认证信息存储到请求状态中
        request.state.current_user = None
        
        response = await call_next(request)
        return response
