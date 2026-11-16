from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse

from core.guardian_guard import get_guardian_context
from hub.app.dtos.guardian import GuardianContext
from visit.adapter.inbound.api.schemas.guardian_report_schema import (
    GuardianMediaItemSchema,
    GuardianMediaPageSchema,
    GuardianPetListSchema,
    GuardianPetSchema,
    GuardianReportItemSchema,
    GuardianReportPageSchema,
    GuardianWeightListSchema,
    GuardianWeightSchema,
)
from visit.adapter.inbound.api.schemas.public_report_schema import PUBLIC_REPORT_HEADERS, PublicReportSchema
from visit.app.dtos.guardian_report_dto import (
    ListGuardianMediaQuery,
    ListGuardianPetsQuery,
    ListGuardianReportsQuery,
    ReadGuardianReportQuery,
    ReadGuardianWeightsQuery,
)
from visit.app.ports.input.list_guardian_media_use_case import ListGuardianMediaUseCase
from visit.app.ports.input.list_guardian_pets_use_case import ListGuardianPetsUseCase
from visit.app.ports.input.list_guardian_reports_use_case import ListGuardianReportsUseCase
from visit.app.ports.input.read_guardian_report_use_case import ReadGuardianReportUseCase
from visit.app.ports.input.read_guardian_weights_use_case import ReadGuardianWeightsUseCase
from visit.dependencies.list_guardian_media_provider import get_list_guardian_media_use_case
from visit.dependencies.list_guardian_pets_provider import get_list_guardian_pets_use_case
from visit.dependencies.list_guardian_reports_provider import get_list_guardian_reports_use_case
from visit.dependencies.read_guardian_report_provider import get_read_guardian_report_use_case
from visit.dependencies.read_guardian_weights_provider import get_read_guardian_weights_use_case

# 보호자(로그인)가 자기 연결의 지난 알림장을 읽는다. 매장의 멤버가 아니라 연결(link_id)이 범위다 —
# 세 경로 모두 보호자 가드(get_guardian_context)를 거친다. 범위 밖 숫자는 DB 에 닿기 전에 422 다.
_Id = Path(ge=1, le=2_147_483_647)

list_guardian_pets_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])
list_guardian_reports_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])
read_guardian_report_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])


@list_guardian_pets_router.get("/links/{link_id}/pets", response_model=GuardianPetListSchema)
async def list_guardian_pets(
    guardian: GuardianContext = Depends(get_guardian_context),
    use_case: ListGuardianPetsUseCase = Depends(get_list_guardian_pets_use_case),
) -> GuardianPetListSchema:
    pets = await use_case.list_pets(ListGuardianPetsQuery(guardian=guardian))
    return GuardianPetListSchema(items=[GuardianPetSchema.model_validate(p) for p in pets])


@list_guardian_reports_router.get("/links/{link_id}/reports", response_model=GuardianReportPageSchema)
async def list_guardian_reports(
    pet_id: Annotated[int | None, Query(ge=1, le=2_147_483_647)] = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    guardian: GuardianContext = Depends(get_guardian_context),
    use_case: ListGuardianReportsUseCase = Depends(get_list_guardian_reports_use_case),
) -> JSONResponse:
    page = await use_case.list_reports(ListGuardianReportsQuery(guardian=guardian, pet_id=pet_id, cursor=cursor))
    body = GuardianReportPageSchema(
        items=[GuardianReportItemSchema.model_validate(i) for i in page.items], next_cursor=page.next_cursor)
    # 서명 주소가 들어 있다 — 중간 캐시에 남지 않게.
    return JSONResponse(body.model_dump(mode="json"), headers=PUBLIC_REPORT_HEADERS)


@read_guardian_report_router.get("/links/{link_id}/reports/{report_id}", response_model=PublicReportSchema)
async def read_guardian_report(
    report_id: Annotated[int, _Id],
    guardian: GuardianContext = Depends(get_guardian_context),
    use_case: ReadGuardianReportUseCase = Depends(get_read_guardian_report_use_case),
) -> JSONResponse:
    view = await use_case.read_report(ReadGuardianReportQuery(guardian=guardian, report_id=report_id))
    return JSONResponse(PublicReportSchema.body(view), headers=PUBLIC_REPORT_HEADERS)


list_guardian_media_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])
read_guardian_weights_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])


# 아이의 사진·영상 모아 보기(⑫) — 최신순 60개씩. 거르기는 아이·연도(매장 시간대)·전후.
@list_guardian_media_router.get("/links/{link_id}/media", response_model=GuardianMediaPageSchema)
async def list_guardian_media(
    pet_id: Annotated[int | None, Query(ge=1, le=2_147_483_647)] = None,
    year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    phase: Literal["after", "before"] | None = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    guardian: GuardianContext = Depends(get_guardian_context),
    use_case: ListGuardianMediaUseCase = Depends(get_list_guardian_media_use_case),
) -> JSONResponse:
    page = await use_case.list_media(
        ListGuardianMediaQuery(guardian=guardian, pet_id=pet_id, year=year, phase=phase, cursor=cursor))
    body = GuardianMediaPageSchema(
        items=[GuardianMediaItemSchema.model_validate(i) for i in page.items], next_cursor=page.next_cursor,
        years=list(page.years))
    return JSONResponse(body.model_dump(mode="json"), headers=PUBLIC_REPORT_HEADERS)


# 아이의 몸무게 변화(⑫) — 오래된 것부터, 매장이 몸무게를 껐으면 비어 있다.
@read_guardian_weights_router.get("/links/{link_id}/pets/{pet_id}/weights", response_model=GuardianWeightListSchema)
async def read_guardian_weights(
    pet_id: Annotated[int, _Id],
    guardian: GuardianContext = Depends(get_guardian_context),
    use_case: ReadGuardianWeightsUseCase = Depends(get_read_guardian_weights_use_case),
) -> JSONResponse:
    found = await use_case.read_weights(ReadGuardianWeightsQuery(guardian=guardian, pet_id=pet_id))
    body = GuardianWeightListSchema(items=[GuardianWeightSchema(visit_date=w.visit_date, weight_kg=float(w.weight_kg))
                                           for w in found])
    return JSONResponse(body.model_dump(mode="json"), headers=PUBLIC_REPORT_HEADERS)

