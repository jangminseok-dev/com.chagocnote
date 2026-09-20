from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.get_me_schema import MeResponseSchema
from auth.app.dtos.get_me_dto import GetMeQuery
from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.dependencies.get_me_provider import get_get_me_use_case
from core.security import get_current_user_id

get_me_router = APIRouter(prefix="/v1", tags=["me"])


@get_me_router.get("/me", response_model=MeResponseSchema)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    use_case: GetMeUseCase = Depends(get_get_me_use_case),
) -> MeResponseSchema:
    me = await use_case.get_me(GetMeQuery(user_id=user_id))
    return MeResponseSchema(
        id=me.id,
        display_name=me.display_name,
        profile_image_url=me.profile_image_url,
        identities=list(me.identities),
    )
