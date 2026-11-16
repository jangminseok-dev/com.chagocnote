from fastapi import APIRouter, Depends

from core.security import get_current_user_id
from guardian.adapter.inbound.api.schemas.guardian_link_schema import GuardianLinkItemSchema, GuardianLinkListSchema
from guardian.app.dtos.list_guardian_links_dto import ListGuardianLinksQuery
from guardian.app.ports.input.list_guardian_links_use_case import ListGuardianLinksUseCase
from guardian.dependencies.list_guardian_links_provider import get_list_guardian_links_use_case

list_guardian_links_router = APIRouter(prefix="/v1/me/guardian", tags=["guardian"])


@list_guardian_links_router.get("/links", response_model=GuardianLinkListSchema)
async def list_guardian_links(
    user_id: int = Depends(get_current_user_id),
    use_case: ListGuardianLinksUseCase = Depends(get_list_guardian_links_use_case),
) -> GuardianLinkListSchema:
    items = await use_case.list_links(ListGuardianLinksQuery(user_id=user_id))
    return GuardianLinkListSchema(items=[
        GuardianLinkItemSchema(link_id=i.link_id, shop_name=i.shop_name, linked_at=i.linked_at, role=i.role,
                               family_count=i.family_count, family_max=i.family_max) for i in items])
