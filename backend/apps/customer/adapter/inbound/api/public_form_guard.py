"""공개 서류 제출의 문 — 본문을 읽기 **전에** 크기와 횟수를 본다(⑪ 설계 F4).

FastAPI 는 의존성을 풀기 전에 본문을 읽는다. 그래서 의존성이 아니라 경로의 처리기를 감싼다.
이 경로는 로그인 없이 본문을 받는 첫 경로다 — 토큰이 없어도 큰 본문을 읽게 하거나 틀린 본문을 끝없이 보낼 수 없어야 한다.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from core.public_client import get_public_client
from customer.adapter.inbound.api.schemas.public_form_schema import PUBLIC_FORM_HEADERS
from customer.dependencies.customer_wiring import build_public_form_limiter

# 서명 그림 65,536바이트의 base64(87,384글자)와 나머지 칸을 넉넉히 덮는다.
MAX_BODY_BYTES = 131_072


def _refuse(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status, headers=PUBLIC_FORM_HEADERS)


class PublicFormSubmitRoute(APIRoute):
    """본문 앞에 서는 문. Content-Length 가 없거나 상한을 넘으면 413, 제출이 10분에 10번을 넘으면 429.

    틀린 본문(422)도 제출 횟수에 든다 — 여기서 센 뒤에 본문을 읽는다.
    """

    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def guarded(request: Request) -> Response:
            length = request.headers.get("content-length", "")
            if not length.isdigit() or int(length) > MAX_BODY_BYTES:
                return _refuse(413, "PAYLOAD_TOO_LARGE", "보낸 내용이 너무 큽니다.")
            if not await build_public_form_limiter().allow_write(get_public_client(request)):
                return _refuse(429, "TOO_MANY_ATTEMPTS", "요청이 너무 잦습니다. 잠시 뒤에 다시 보내 주세요.")
            return await handler(request)

        return guarded
