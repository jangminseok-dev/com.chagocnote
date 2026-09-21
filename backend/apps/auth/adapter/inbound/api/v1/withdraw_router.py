from fastapi import APIRouter, BackgroundTasks, Depends, Response, status

from auth.adapter.inbound.api.schemas.withdraw_schema import WithdrawRequestSchema
from auth.app.dtos.withdraw_dto import WithdrawCommand
from auth.app.ports.input.withdraw_use_case import WithdrawUseCase
from auth.app.services.provider_revoker import ProviderRevoker
from auth.dependencies.provider_revoker_provider import get_provider_revoker
from auth.dependencies.withdraw_provider import get_withdraw_use_case
from core.security import get_current_user_id

withdraw_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@withdraw_router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw(
    tasks: BackgroundTasks,
    body: WithdrawRequestSchema | None = None,
    user_id: int = Depends(get_current_user_id),
    use_case: WithdrawUseCase = Depends(get_withdraw_use_case),
    revoker: ProviderRevoker = Depends(get_provider_revoker),
) -> Response:
    result = await use_case.withdraw(
        WithdrawCommand(
            user_id=user_id,
            confirm_close_shops=body.confirm_close_shops if body else False,
        )
    )
    # 제공자 쪽 연결 끊기는 DB 커밋이 끝난 뒤에 돈다. 실패해도 탈퇴는 이미 끝났다 (로그만 남는다).
    tasks.add_task(revoker.revoke_all, list(result.revocations))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
