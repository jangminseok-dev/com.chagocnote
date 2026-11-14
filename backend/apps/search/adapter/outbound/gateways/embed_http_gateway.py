"""임베딩 프로세스(compose 의 embed)를 부르는 어댑터. 실패는 예외가 아니라 "없음"이다 — 검색은 글자만으로 답하고
색인기는 줄을 남겨 뒤에 다시 한다. 글·벡터·응답 본문·예외 문자열을 로그에 남기지 않는다(아무것도 찍지 않는다)."""
from __future__ import annotations

import asyncio
import math

import httpx

from search.app.ports.output.embedding_port import DIMENSIONS, Embedded, EmbeddingPort
from search.domain.services.embedding_model import CURRENT_MODEL

MAX_TEXTS = 64   # 임베딩 프로세스가 한 번에 받는 글 수(embed/app.py)


def _vectors(payload: object, expected: int) -> tuple[tuple[float, ...], ...] | None:
    """답의 모양·모델·개수·차원이 맞을 때만 벡터들. 하나라도 어긋나면 None."""
    if not isinstance(payload, dict) or payload.get("model") != CURRENT_MODEL:
        return None
    vectors = payload.get("vectors")
    if not isinstance(vectors, list) or len(vectors) != expected:
        return None
    result = []
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != DIMENSIONS:
            return None
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in vector):
            return None
        result.append(tuple(float(x) for x in vector))
    return tuple(result)


class EmbedHttpGateway(EmbeddingPort):
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._url = base_url.rstrip("/") + "/embed"
        self._client = client if client is not None else httpx.AsyncClient()

    async def embed(self, kind: str, texts: list[str], timeout: float) -> Embedded | None:
        if not texts:
            return Embedded(model=CURRENT_MODEL, vectors=())
        try:
            return await asyncio.wait_for(self._embed(kind, texts), timeout)   # 전체에 대한 시간 제한
        except (TimeoutError, httpx.HTTPError, ValueError):
            return None

    async def _embed(self, kind: str, texts: list[str]) -> Embedded | None:
        collected: list[tuple[float, ...]] = []
        for start in range(0, len(texts), MAX_TEXTS):
            chunk = texts[start:start + MAX_TEXTS]
            response = await self._client.post(self._url, json={"kind": kind, "texts": chunk})
            if response.status_code != 200:
                return None
            vectors = _vectors(response.json(), len(chunk))   # 깨진 본문은 ValueError
            if vectors is None:
                return None
            collected.extend(vectors)
        return Embedded(model=CURRENT_MODEL, vectors=tuple(collected))


class NoEmbedding(EmbeddingPort):
    """임베딩 프로세스의 주소가 없을 때(EMBED_BASE_URL 이 빔) — 뜻 검색 없이 글자 검색만 한다."""

    async def embed(self, kind: str, texts: list[str], timeout: float) -> Embedded | None:
        return None
