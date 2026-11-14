"""임베딩 프로세스를 부르는 어댑터 — 실패는 전부 "없음"이고 던지지 않는다. 글을 로그에 남기지 않는다."""
import asyncio
import json
import logging

import httpx
import pytest

from search.adapter.outbound.gateways.embed_http_gateway import EmbedHttpGateway, NoEmbedding
from search.app.ports.output.embedding_port import DIMENSIONS, Embedded
from search.domain.services.embedding_model import CURRENT_MODEL

SECRET = "귀를 만지면 무는 아이"
VECTOR = [0.5] * DIMENSIONS


def _gateway(handler) -> EmbedHttpGateway:
    return EmbedHttpGateway("http://embed:8100", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def _ok(vectors, model=CURRENT_MODEL):
    return lambda request: httpx.Response(200, json={"model": model, "vectors": vectors})


async def test_글을_보내고_벡터를_받는다():
    seen = []

    def handler(request):
        seen.append((request.method, str(request.url), json.loads(request.content)))
        return httpx.Response(200, json={"model": CURRENT_MODEL, "vectors": [VECTOR, VECTOR]})

    result = await _gateway(handler).embed("passage", ["가", "나"], 10.0)
    assert result == Embedded(model=CURRENT_MODEL, vectors=(tuple(VECTOR), tuple(VECTOR)))
    assert seen == [("POST", "http://embed:8100/embed", {"kind": "passage", "texts": ["가", "나"]})]


async def test_빈_목록은_부르지_않는다():
    def handler(request):
        raise AssertionError("부르면 안 된다")

    assert await _gateway(handler).embed("passage", [], 10.0) == Embedded(model=CURRENT_MODEL, vectors=())


async def test_한_번에_64개씩_나눠_보낸다():
    sizes = []

    def handler(request):
        texts = json.loads(request.content)["texts"]
        sizes.append(len(texts))
        return httpx.Response(200, json={"model": CURRENT_MODEL, "vectors": [VECTOR] * len(texts)})

    result = await _gateway(handler).embed("passage", ["글"] * 70, 10.0)
    assert sizes == [64, 6] and len(result.vectors) == 70


@pytest.mark.parametrize("handler", [
    lambda request: httpx.Response(500, json={"code": "INTERNAL"}),
    lambda request: httpx.Response(422, json={"code": "VALIDATION_ERROR"}),
    lambda request: httpx.Response(200, content=b"<html>"),
    lambda request: httpx.Response(200, json=[1, 2, 3]),
    lambda request: httpx.Response(200, json={"model": CURRENT_MODEL}),
    _ok([[0.5] * (DIMENSIONS - 1)]),                    # 차원이 다르다
    _ok([VECTOR, VECTOR]),                              # 개수가 다르다
    _ok([]),
    _ok([["a"] * DIMENSIONS]),                          # 수가 아니다
    _ok([[float("nan")] + VECTOR[1:]]) if False else _ok([None]),
    _ok([VECTOR], model="another-model"),               # 다른 모델의 벡터는 쓰지 않는다
], ids=["500", "422", "깨진_본문", "목록", "칸_없음", "차원", "개수", "빈_벡터", "수_아님", "null", "다른_모델"])
async def test_깨진_답은_없음이다(handler):
    assert await _gateway(handler).embed("query", [SECRET], 1.5) is None


async def test_연결이_안_되면_없음이다():
    def handler(request):
        raise httpx.ConnectError("refused")

    assert await _gateway(handler).embed("query", [SECRET], 1.5) is None


async def test_시간_제한을_넘기면_없음이다():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json={"model": CURRENT_MODEL, "vectors": [VECTOR]})

    started = asyncio.get_running_loop().time()
    assert await _gateway(handler).embed("query", [SECRET], 0.05) is None
    assert asyncio.get_running_loop().time() - started < 0.5


async def test_실패해도_글이_로그에_남지_않는다(caplog):
    def handler(request):
        raise httpx.ConnectError(f"connect failed while sending {SECRET}")

    with caplog.at_level(logging.DEBUG):
        assert await _gateway(handler).embed("query", [SECRET], 1.5) is None
    assert SECRET not in caplog.text


async def test_주소가_없으면_늘_없음이다():
    assert await NoEmbedding().embed("query", [SECRET], 1.5) is None
