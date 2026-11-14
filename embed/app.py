"""임베딩 프로세스 — 안쪽 HTTP 하나(POST /embed). 게이트웨이에 싣지 않고 compose 내부망에서만 부른다.

글과 벡터를 로그·오류 응답에 남기지 않는다. 로그는 건수와 걸린 시간뿐이다.
"""
from __future__ import annotations

import asyncio
import logging
import time
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from encoder import MODEL_DIR, MODEL_NAME, Encoder

logger = logging.getLogger("embed")

MAX_TEXTS = 64
MAX_CHARS = 4000


class EmbedRequest(BaseModel):
    kind: Literal["query", "passage"]
    texts: Annotated[list[Annotated[str, StringConstraints(max_length=MAX_CHARS)]],
                     Field(min_length=1, max_length=MAX_TEXTS)]


class EmbedResponse(BaseModel):
    model: str
    vectors: list[list[float]]


@lru_cache(maxsize=1)
def get_encoder() -> Encoder:
    """프로세스에 하나. 첫 요청이 아니라 기동 때 올린다(lifespan)."""
    return Encoder(MODEL_DIR)


async def _lifespan(_: FastAPI):
    get_encoder()
    yield


app = FastAPI(title="차곡노트 임베딩", lifespan=_lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
    """기본 422 는 받은 값을 되돌려 준다 — 글이 응답과 그 로그에 남지 않게 고정된 본문만 준다."""
    return JSONResponse(
        status_code=422, content={"code": "VALIDATION_ERROR", "message": "요청 형식이 올바르지 않습니다."}
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/embed")
async def embed(body: EmbedRequest) -> EmbedResponse:
    started = time.perf_counter()
    vectors = await asyncio.to_thread(get_encoder().encode, body.kind, body.texts)   # 추론이 루프를 막지 않게
    logger.info("%s %d건 %dms", body.kind, len(body.texts), (time.perf_counter() - started) * 1000)
    return EmbedResponse(model=MODEL_NAME, vectors=vectors)
