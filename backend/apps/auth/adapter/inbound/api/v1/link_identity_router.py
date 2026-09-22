from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.link_identity_schema import (
    IdentitiesResponseSchema,
    LinkIdentityRequestSchema,
)
from auth.app.dtos.link_identity_dto import LinkIdentityCommand
from auth.app.ports.input.link_identity_use_case import LinkIdentityUseCase
from auth.dependencies.link_identity_provider import get_link_identity_use_case
from core.security import RecentLogin, require_recent_login

link_identity_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@link_identity_router.post("/identities", response_model=IdentitiesResponseSchema)
async def link_identity(
    body: LinkIdentityRequestSchema,
    recent: RecentLogin = Depends(require_recent_login),
    use_case: LinkIdentityUseCase = Depends(get_link_identity_use_case),
) -> IdentitiesResponseSchema:
    result = await use_case.link(
        LinkIdentityCommand(
            user_id=recent.user_id,
            provider=body.provider,
            token=body.token,
            authorization_code=body.authorization_code,
            nonce=body.nonce,
        )
    )
    return IdentitiesResponseSchema(identities=list(result.identities))
