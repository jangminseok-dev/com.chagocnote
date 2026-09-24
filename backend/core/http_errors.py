"""오류 응답을 {"code", "message"} 한 가지 형식으로 통일한다."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.hub_errors import HUB_ERROR_STATUS


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def install_error_handlers(app: FastAPI, domain_errors: dict[type[Exception], int]) -> None:
    """ApiError 와 스포크의 도메인 오류, 허브 포트 오류를 같은 형식의 응답으로 바꾼다.

    domain_errors 는 {도메인 예외 클래스: HTTP 상태 코드}. 예외는 code 속성을 가져야 한다.
    허브 포트 오류(`core/hub_errors.py`)는 어느 프로세스에서든 같은 상태로 나가야 하므로 여기서 함께 등록한다.
    """

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )

    def _make(status_code: int):
        async def _handler(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(
                status_code=status_code,
                content={"code": getattr(exc, "code"), "message": str(exc)},
            )

        return _handler

    for exc_type, status_code in {**HUB_ERROR_STATUS, **domain_errors}.items():
        app.add_exception_handler(exc_type, _make(status_code))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION_ERROR", "message": "요청 형식이 올바르지 않습니다."},
        )

    _STARLETTE_CODE = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": _STARLETTE_CODE.get(exc.status_code, "HTTP_ERROR"),
                "message": str(exc.detail),
            },
        )
