from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.refresh_token_schema import (
    RefreshRequestSchema,
    RefreshResponseSchema,
)
from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.ports.input.refresh_token_use_case import RefreshTokenUseCase
from auth.dependencies.refresh_token_provider import get_refresh_token_use_case

refresh_token_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@refresh_token_router.post("/refresh", response_model=RefreshResponseSchema)
async def refresh_token(
    body: RefreshRequestSchema,
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
) -> RefreshResponseSchema:
    pair = await use_case.refresh(RefreshTokenCommand(refresh_token=body.refresh_token))
    return RefreshResponseSchema(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )
