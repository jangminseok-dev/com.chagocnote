"""API 프로세스 — 공개키로 토큰을 검증만 한다. 토큰을 발급할 수 없다."""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from fastapi import FastAPI

from core.database import dispose_engine, init_engine
from core.redis import dispose_redis

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.get_me_router import get_me_router
from core.http_errors import install_error_handlers
from core.shop_guard import get_shop_access_port
from auth.dependencies.check_operator_provider import get_check_operator_use_case
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
from platform_admin.dependencies.hub_ports import get_operator_directory
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS
from tenancy.adapter.inbound.api.v1.tenancy_myself_router import tenancy_myself_router
from tenancy.dependencies.resolve_shop_access_provider import get_resolve_shop_access_use_case


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    try:
        yield
    finally:
        await dispose_engine()
        await dispose_redis()


app = FastAPI(title="차곡노트 API", lifespan=lifespan)
app.include_router(get_me_router)
app.include_router(tenancy_myself_router)
app.include_router(platform_myself_router)
install_error_handlers(
    app, {**AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS}
)

# 허브 포트 조립 — 스포크끼리는 서로를 모른다. 소비하는 쪽의 "자리"에 구현하는 쪽의 프로바이더를 꽂는다.
app.dependency_overrides[get_shop_access_port] = get_resolve_shop_access_use_case
app.dependency_overrides[get_operator_directory] = get_check_operator_use_case


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "backend"}
