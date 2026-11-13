from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from core.security import get_current_user_id
from guardian.adapter.inbound.api.schemas.guardian_link_schema import GuardianLinkCreatedSchema
from guardian.app.dtos.claim_guardian_link_dto import ClaimGuardianLinkCommand
from guardian.app.ports.input.claim_guardian_link_use_case import ClaimGuardianLinkUseCase
from guardian.dependencies.claim_guardian_link_provider import get_claim_guardian_link_use_case

claim_guardian_link_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])


# 알림장 토큰은 헤더로만 받는다 — 경로·질의·본문에 두면 접속 기록에 남는다.
# 헤더가 없거나 이상해도 422 가 아니라 404 다(유스케이스가 판정한다) — 그래서 선택 값으로 받는다.
@claim_guardian_link_router.post(
    "/links", response_model=GuardianLinkCreatedSchema, status_code=201,
    responses={200: {"model": GuardianLinkCreatedSchema, "description": "이미 내 연결이다"}},
)
async def claim_guardian_link(
    x_report_token: Annotated[str | None, Header()] = None,
    user_id: int = Depends(get_current_user_id),
    use_case: ClaimGuardianLinkUseCase = Depends(get_claim_guardian_link_use_case),
) -> JSONResponse:
    result = await use_case.claim(ClaimGuardianLinkCommand(user_id=user_id, token=x_report_token))
    return JSONResponse({"link_id": result.link_id}, status_code=201 if result.created else 200)
