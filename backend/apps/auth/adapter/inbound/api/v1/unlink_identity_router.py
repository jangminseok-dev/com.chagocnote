from fastapi import APIRouter, BackgroundTasks, Depends

from auth.adapter.inbound.api.schemas.unlink_identity_schema import UnlinkIdentityResponseSchema
from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand
from auth.app.ports.input.unlink_identity_use_case import UnlinkIdentityUseCase
from auth.app.services.provider_revoker import ProviderRevoker
from auth.dependencies.provider_revoker_provider import get_provider_revoker
from auth.dependencies.recent_login_guard import RecentLogin, require_recent_login
from auth.dependencies.unlink_identity_provider import get_unlink_identity_use_case

unlink_identity_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@unlink_identity_router.delete(
    "/identities/{provider}", response_model=UnlinkIdentityResponseSchema
)
async def unlink_identity(
    provider: str,
    tasks: BackgroundTasks,
    recent: RecentLogin = Depends(require_recent_login),
    use_case: UnlinkIdentityUseCase = Depends(get_unlink_identity_use_case),
    revoker: ProviderRevoker = Depends(get_provider_revoker),
) -> UnlinkIdentityResponseSchema:
    result = await use_case.unlink(
        UnlinkIdentityCommand(
            user_id=recent.user_id, provider=provider, auth_time=recent.auth_time
        )
    )
    # 제공자 쪽 연결 끊기는 DB 커밋이 끝난 뒤에 돈다. 잠금을 쥔 채 외부 HTTP 를 부르지 않는다.
    tasks.add_task(revoker.revoke_all, [result.revocation])
    return UnlinkIdentityResponseSchema(
        identities=list(result.identities),
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=result.tokens.expires_in,
    )
