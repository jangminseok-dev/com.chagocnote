from fastapi import APIRouter, Depends, Response, status

from auth.adapter.inbound.api.schemas.logout_schema import LogoutRequestSchema
from auth.app.dtos.logout_dto import LogoutCommand
from auth.app.ports.input.logout_use_case import LogoutUseCase
from auth.dependencies.logout_provider import get_logout_use_case

logout_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@logout_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequestSchema,
    use_case: LogoutUseCase = Depends(get_logout_use_case),
) -> Response:
    await use_case.logout(LogoutCommand(refresh_token=body.refresh_token))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
