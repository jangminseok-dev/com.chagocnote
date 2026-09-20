"""인증 프로세스 — JWT 개인키를 가진 유일한 프로세스. /v1/auth/* 만 맡는다."""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from core.singleton.secret_manager import get_secret_manager

# 컨테이너는 env_file 로 주입받는다. 이 호출은 컨테이너 밖에서 돌릴 때를 위한 것이다.
get_secret_manager().load_auth_env()

from fastapi import FastAPI

from core.database import dispose_engine, init_engine
from core.redis import dispose_redis
from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.auth_myself_router import auth_myself_router
from auth.adapter.inbound.api.v1.logout_router import logout_router
from auth.adapter.inbound.api.v1.refresh_token_router import refresh_token_router
from auth.adapter.inbound.api.v1.social_login_router import social_login_router
from core.http_errors import install_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    try:
        yield
    finally:
        await dispose_engine()
        await dispose_redis()


app = FastAPI(title="차곡노트 Auth", lifespan=lifespan)
app.include_router(auth_myself_router)
app.include_router(social_login_router)
app.include_router(refresh_token_router)
app.include_router(logout_router)
install_error_handlers(app, AUTH_ERROR_STATUS)


@app.get("/v1/auth/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "auth"}
