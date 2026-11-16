from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from core.public_client import get_public_client
from customer.adapter.inbound.api.public_form_guard import PublicFormSubmitRoute
from customer.adapter.inbound.api.schemas.public_form_schema import (
    PUBLIC_FORM_HEADERS, SubmitPublicIntakeRequestSchema,
)
from customer.app.dtos.public_form_dto import SubmitPublicIntakeCommand
from customer.app.ports.input.submit_public_intake_use_case import SubmitPublicIntakeUseCase
from customer.dependencies.submit_public_intake_provider import get_submit_public_intake_use_case

# 본문을 읽기 전에 크기와 제출 횟수를 본다(public_form_guard) — 동의서 제출과 같은 한도다.
submit_public_intake_router = APIRouter(prefix="/v1/public", tags=["public"], route_class=PublicFormSubmitRoute)


# 로그인이 없다. 보호자의 브라우저가 낸 것을 웹 서버가 대신 보낸다. 토큰은 헤더로만 받는다.
@submit_public_intake_router.post("/form/intake", status_code=204)
async def submit_public_intake(
    body: SubmitPublicIntakeRequestSchema,
    x_form_token: Annotated[str | None, Header()] = None,
    client: str = Depends(get_public_client),
    use_case: SubmitPublicIntakeUseCase = Depends(get_submit_public_intake_use_case),
) -> Response:
    await use_case.submit_public_intake(SubmitPublicIntakeCommand(
        token=x_form_token, client=client, entry=body.to_entry(), done=body.done,
        consent=None if body.consent is None else body.consent.to_entry()))
    return Response(status_code=204, headers=PUBLIC_FORM_HEADERS)
