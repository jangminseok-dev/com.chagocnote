from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from core.public_client import get_public_client
from customer.adapter.inbound.api.schemas.public_form_schema import (
    PUBLIC_FORM_HEADERS, PublicOpenFormSchema, PublicOpenIntakeSchema, PublicSubmittedFormSchema, public_form_body,
)
from customer.app.dtos.public_form_dto import ReadPublicFormQuery
from customer.app.ports.input.read_public_form_use_case import ReadPublicFormUseCase
from customer.dependencies.read_public_form_provider import get_read_public_form_use_case

read_public_form_router = APIRouter(prefix="/v1/public", tags=["public"])


# 로그인이 없다. 토큰은 헤더로만 받는다 — 경로·질의에 두면 접속 기록에 남는다.
# 헤더가 없거나 이상해도 422 가 아니라 404 다(유스케이스가 판정한다) — 그래서 선택 값으로 받는다.
@read_public_form_router.get("/form", response_model=PublicOpenFormSchema | PublicOpenIntakeSchema | PublicSubmittedFormSchema)
async def read_public_form(
    x_form_token: Annotated[str | None, Header()] = None,
    client: str = Depends(get_public_client),
    use_case: ReadPublicFormUseCase = Depends(get_read_public_form_use_case),
) -> JSONResponse:
    view = await use_case.read_public_form(ReadPublicFormQuery(token=x_form_token, client=client))
    return JSONResponse(public_form_body(view), headers=PUBLIC_FORM_HEADERS)
