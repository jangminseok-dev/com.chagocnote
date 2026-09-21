import time

import httpx
import pytest
from jose import jwt

from auth.adapter.outbound.strategy.jwks_verifier import http_jwks_fetchers, verify_with_jwks
from auth.domain.errors import ProviderVerificationError
from auth.tests.helpers.keys import make_rsa_keypair

OLD_PEM, _, OLD_JWK = make_rsa_keypair(kid="old-kid")
NEW_PEM, _, NEW_JWK = make_rsa_keypair(kid="new-kid")


def _token(pem, kid):
    claims = {"iss": "issuer", "aud": "app", "sub": "user-1", "exp": int(time.time()) + 600}
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


def _fetchers(keysets, clock, status=200):
    """keysets 를 호출 순서대로 하나씩 돌려주는 가짜 제공자. 호출 횟수를 센다."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(status, json={"keys": keysets[min(len(calls) - 1, len(keysets) - 1)]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetch, refetch = http_jwks_fetchers(http, "https://provider.test/keys", now=lambda: clock["t"])
    return fetch, refetch, calls


async def test_캐시에_없는_kid_면_한_번_다시_받아_검증한다():
    clock = {"t": 1000.0}
    fetch, refetch, calls = _fetchers([[OLD_JWK], [OLD_JWK, NEW_JWK]], clock)
    await verify_with_jwks(_token(OLD_PEM, "old-kid"), fetch, ("issuer",), ("app",), refetch)
    clock["t"] += 120   # 제공자가 키를 바꿨다
    claims = await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",), refetch)
    assert claims["sub"] == "user-1"
    assert len(calls) == 2


async def test_다시_받아도_없는_kid_면_거절한다():
    clock = {"t": 1000.0}
    fetch, refetch, _ = _fetchers([[OLD_JWK]], clock)
    clock["t"] += 120
    with pytest.raises(ProviderVerificationError):
        await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",), refetch)


async def test_강제_재조회는_간격_안에서는_한_번만_한다():
    """D1 — 모르는 kid 를 쏟아부어도 제공자를 60초에 한 번만 두드린다."""
    clock = {"t": 1000.0}
    fetch, refetch, calls = _fetchers([[OLD_JWK]], clock)
    for _ in range(5):
        with pytest.raises(ProviderVerificationError):
            await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",), refetch)
    assert len(calls) == 1   # 첫 조회가 곧 최신 값이라, 60초 안의 강제 재조회는 캐시를 돌려준다
    clock["t"] += 61
    with pytest.raises(ProviderVerificationError):
        await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",), refetch)
    assert len(calls) == 2


async def test_공개키를_받지_못하면_검증_실패로_돌려준다():
    fetch, refetch, _ = _fetchers([[OLD_JWK]], {"t": 1000.0}, status=503)
    with pytest.raises(ProviderVerificationError):
        await verify_with_jwks(_token(OLD_PEM, "old-kid"), fetch, ("issuer",), ("app",), refetch)


async def test_재조회_함수가_없으면_캐시만_본다():
    async def fetch():
        return {"keys": [OLD_JWK]}

    with pytest.raises(ProviderVerificationError):
        await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",))
