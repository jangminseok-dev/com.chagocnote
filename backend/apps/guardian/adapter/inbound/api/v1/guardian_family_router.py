"""가족과 함께 보기(⑫ 설계 3.5)의 보호자 경로. 전부 로그인 뒤다 — 가족 잇기도 로그인한 계정으로만."""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Response
from fastapi.responses import JSONResponse

from core.security import get_current_user_id
from guardian.adapter.inbound.api.schemas.guardian_family_schema import (
    FamilyInviteSchema, FamilyListSchema, FamilyMemberSchema,
)
from guardian.adapter.inbound.api.schemas.guardian_link_schema import GuardianLinkCreatedSchema
from guardian.app.dtos.family_dto import (
    CreateFamilyInviteCommand, EndAllFamilyCommand, EndFamilyMemberCommand, JoinFamilyCommand, ListFamilyQuery,
)
from guardian.app.ports.input.create_family_invite_use_case import CreateFamilyInviteUseCase
from guardian.app.ports.input.end_all_family_use_case import EndAllFamilyUseCase
from guardian.app.ports.input.end_family_member_use_case import EndFamilyMemberUseCase
from guardian.app.ports.input.join_family_use_case import JoinFamilyUseCase
from guardian.app.ports.input.list_family_use_case import ListFamilyUseCase
from guardian.dependencies.family_providers import (
    get_create_family_invite_use_case, get_end_all_family_use_case, get_end_family_member_use_case,
    get_join_family_use_case, get_list_family_use_case,
)

guardian_family_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])
LinkId = Annotated[int, Path(ge=1, le=2_147_483_647)]


@guardian_family_router.post("/links/{link_id}/family-invites", response_model=FamilyInviteSchema, status_code=201)
async def create_family_invite(
    link_id: LinkId,
    user_id: int = Depends(get_current_user_id),
    use_case: CreateFamilyInviteUseCase = Depends(get_create_family_invite_use_case),
) -> JSONResponse:
    result = await use_case.create(CreateFamilyInviteCommand(user_id=user_id, link_id=link_id))
    body = FamilyInviteSchema(code=result.code, expires_at=result.expires_at).model_dump(mode="json")
    # 코드가 든 응답은 어디에도 저장되지 않게 한다.
    return JSONResponse(body, status_code=201, headers={"Cache-Control": "no-store"})


# 초대 코드는 헤더로만 받는다 — 경로·질의·본문에 두면 접속 기록에 남는다. 없거나 이상해도 422 가 아니라 404 다.
@guardian_family_router.post(
    "/family-links", response_model=GuardianLinkCreatedSchema, status_code=201,
    responses={200: {"model": GuardianLinkCreatedSchema, "description": "이미 그 기록을 보는 계정이다"}},
)
async def join_family(
    x_family_invite: Annotated[str | None, Header()] = None,
    user_id: int = Depends(get_current_user_id),
    use_case: JoinFamilyUseCase = Depends(get_join_family_use_case),
) -> JSONResponse:
    result = await use_case.join(JoinFamilyCommand(user_id=user_id, code=x_family_invite))
    return JSONResponse({"link_id": result.link_id}, status_code=201 if result.created else 200)


@guardian_family_router.get("/links/{link_id}/family", response_model=FamilyListSchema)
async def list_family(
    link_id: LinkId,
    user_id: int = Depends(get_current_user_id),
    use_case: ListFamilyUseCase = Depends(get_list_family_use_case),
) -> FamilyListSchema:
    items = await use_case.list_family(ListFamilyQuery(user_id=user_id, link_id=link_id))
    return FamilyListSchema(items=[
        FamilyMemberSchema(family_id=i.family_id, linked_at=i.linked_at, unseen=i.unseen) for i in items])


@guardian_family_router.delete("/links/{link_id}/family/{family_id}", status_code=204)
async def end_family_member(
    link_id: LinkId,
    family_id: LinkId,
    user_id: int = Depends(get_current_user_id),
    use_case: EndFamilyMemberUseCase = Depends(get_end_family_member_use_case),
) -> Response:
    await use_case.end_member(EndFamilyMemberCommand(user_id=user_id, link_id=link_id, family_id=family_id))
    return Response(status_code=204)


@guardian_family_router.delete("/links/{link_id}/family", status_code=204)
async def end_all_family(
    link_id: LinkId,
    user_id: int = Depends(get_current_user_id),
    use_case: EndAllFamilyUseCase = Depends(get_end_all_family_use_case),
) -> Response:
    await use_case.end_all(EndAllFamilyCommand(user_id=user_id, link_id=link_id))
    return Response(status_code=204)
