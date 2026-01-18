from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Union
import logging


logger = logging.getLogger(__name__)


class MangoException(Exception):
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(self.message)


async def mango_exception_handler(request: Request, exc: MangoException):
    logger.error(f"MangoException: {exc.message}")
    return JSONResponse(
        status_code=exc.code,
        content={"message": exc.message, "success": False}
    )


class AuthenticationException(MangoException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)


class AuthorizationException(MangoException):
    def __init__(self, message: str = "Authorization failed"):
        super().__init__(message, 403)


class ResourceNotFoundException(MangoException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class ValidationException(MangoException):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, 422)


# FastAPI exception handlers
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail), "success": False}
    )


async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"General exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "success": False}
    )
