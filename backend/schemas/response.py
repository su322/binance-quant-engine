from typing import Generic, TypeVar, Optional
from pydantic import BaseModel
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "Success"
    data: Optional[T] = None


class EmptyResponse(BaseModel):
    pass


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    处理 HTTP 异常
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardResponse[None](
            code=exc.status_code, message=str(exc.detail), data=None
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理请求参数验证异常
    """
    return JSONResponse(
        status_code=422,
        content=StandardResponse[list](
            code=422, message="Validation Error", data=exc.errors()
        ).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception):
    """
    处理所有未捕获的异常
    """
    return JSONResponse(
        status_code=500,
        content=StandardResponse[None](
            code=500, message=f"Internal Server Error: {str(exc)}", data=None
        ).model_dump(),
    )
