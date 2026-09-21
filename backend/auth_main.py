"""인증 프로세스 — JWT 개인키를 가진 유일한 프로세스. /v1/auth/* 만 맡는다.

회원 탈퇴가 소속을 정리해야 해서 tenancy 의 MembershipLifecyclePort 구현을 여기서 꽂는다.
"""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from core.singleton.secret_manager import get_secret_manager

# 컨테이너는 env_file 로 주입받는다. 이 호출은 컨테이너 밖에서 돌릴 때를 위한 것이다.
get_secret_manager().load_auth_env()

import core.auth_config  # noqa: F401 — 개인키가 없으면 기동 단계에서 바로 실패하게 한다

from fastapi import FastAPI

from core.database import dispose_engine, init_engine
from core.redis import dispose_redis
from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.dependencies.auth_wiring import dispose_http
from auth.adapter.inbound.api.v1.auth_myself_router import auth_myself_router
from auth.adapter.inbound.api.v1.link_identity_router import link_identity_router
from auth.adapter.inbound.api.v1.logout_router import logout_router
from auth.adapter.inbound.api.v1.refresh_token_router import refresh_token_router
from auth.adapter.inbound.api.v1.social_login_router import social_login_router
from auth.adapter.inbound.api.v1.unlink_identity_router import unlink_identity_router
from auth.adapter.inbound.api.v1.withdraw_router import withdraw_router
from auth.dependencies.hub_ports import get_membership_lifecycle
from core.http_errors import install_error_handlers
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS
from tenancy.dependencies.apply_withdrawal_provider import get_apply_withdrawal_use_case


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    try:
        yield
    finally:
        await dispose_http()
        await dispose_engine()
        await dispose_redis()


app = FastAPI(title="차곡노트 Auth", lifespan=lifespan)
app.include_router(auth_myself_router)
app.include_router(social_login_router)
app.include_router(refresh_token_router)
app.include_router(logout_router)
app.include_router(link_identity_router)
app.include_router(unlink_identity_router)
app.include_router(withdraw_router)
# 탈퇴가 tenancy 의 소속 정리를 부른다. 그쪽 도메인 오류(409)도 이 프로세스에서 HTTP 로 바뀌어야 한다.
install_error_handlers(app, {**AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS})

# 허브 포트 조립 — 스포크끼리는 서로를 모른다. 소비하는 쪽의 "자리"에 구현하는 쪽의 프로바이더를 꽂는다.
app.dependency_overrides[get_membership_lifecycle] = get_apply_withdrawal_use_case


@app.get("/v1/auth/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "auth"}
