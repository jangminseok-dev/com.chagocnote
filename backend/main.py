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
install_error_handlers(app, AUTH_ERROR_STATUS)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "backend"}
