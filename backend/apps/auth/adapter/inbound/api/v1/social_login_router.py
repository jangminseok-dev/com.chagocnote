from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.social_login_schema import (
    SocialLoginRequestSchema,
    TokenResponseSchema,
)
from auth.app.dtos.social_login_dto import SocialLoginCommand
from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.dependencies.social_login_provider import get_social_login_use_case

social_login_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@social_login_router.post("/social", response_model=TokenResponseSchema)
async def social_login(
    body: SocialLoginRequestSchema,
    use_case: SocialLoginUseCase = Depends(get_social_login_use_case),
) -> TokenResponseSchema:
    result = await use_case.login(
        SocialLoginCommand(
            provider=body.provider,
            token=body.token,
            authorization_code=body.authorization_code,
            nonce=body.nonce,
            display_name=body.display_name,
        )
    )
    return TokenResponseSchema(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=result.tokens.expires_in,
        user_id=result.user_id,
        is_new_user=result.is_new_user,
    )
