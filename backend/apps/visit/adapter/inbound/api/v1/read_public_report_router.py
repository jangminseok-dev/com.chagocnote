from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from visit.adapter.inbound.api.schemas.public_report_schema import PUBLIC_REPORT_HEADERS, PublicReportSchema
from visit.app.dtos.read_public_report_dto import ReadPublicReportQuery
from visit.app.ports.input.read_public_report_use_case import ReadPublicReportUseCase
from core.public_client import get_public_client
from visit.dependencies.read_public_report_provider import get_read_public_report_use_case

read_public_report_router = APIRouter(prefix="/v1/public", tags=["public"])


# 로그인이 없다. 토큰은 헤더로만 받는다 — 경로·질의에 두면 접속 기록에 남는다.
# 헤더가 없거나 이상해도 422 가 아니라 404 다(유스케이스가 판정한다) — 그래서 선택 값으로 받는다.
@read_public_report_router.get("/report", response_model=PublicReportSchema)
async def read_public_report(
    x_report_token: Annotated[str | None, Header()] = None,
    client: str = Depends(get_public_client),
    use_case: ReadPublicReportUseCase = Depends(get_read_public_report_use_case),
) -> JSONResponse:
    view = await use_case.read_public_report(ReadPublicReportQuery(token=x_report_token, client=client))
    return JSONResponse(PublicReportSchema.body(view), headers=PUBLIC_REPORT_HEADERS)
