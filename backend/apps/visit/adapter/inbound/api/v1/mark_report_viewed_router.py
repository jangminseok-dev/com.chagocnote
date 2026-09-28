from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from visit.adapter.inbound.api.schemas.public_report_schema import PUBLIC_REPORT_HEADERS
from visit.app.dtos.mark_report_viewed_dto import MarkReportViewedCommand
from visit.app.ports.input.mark_report_viewed_use_case import MarkReportViewedUseCase
from visit.dependencies.mark_report_viewed_provider import get_mark_report_viewed_use_case
from visit.dependencies.public_client import get_public_client

mark_report_viewed_router = APIRouter(prefix="/v1/public", tags=["public"])


# 로그인이 없다. 보호자의 브라우저가 알림장을 열었을 때 웹 서버를 거쳐 온다(미리보기 로봇은 보내지 않는다).
@mark_report_viewed_router.post("/report/viewed", status_code=204)
async def mark_report_viewed(
    x_report_token: Annotated[str | None, Header()] = None,
    client: str = Depends(get_public_client),
    use_case: MarkReportViewedUseCase = Depends(get_mark_report_viewed_use_case),
) -> Response:
    await use_case.mark_report_viewed(MarkReportViewedCommand(token=x_report_token, client=client))
    return Response(status_code=204, headers=PUBLIC_REPORT_HEADERS)
