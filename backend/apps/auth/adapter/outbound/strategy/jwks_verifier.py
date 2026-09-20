"""구글·Apple 전략이 함께 쓰는 ID 토큰 서명 검증."""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import httpx
from jose import JWTError, jwt

from auth.domain.errors import ProviderVerificationError

JwksFetcher = Callable[[], Awaitable[dict]]


async def verify_with_jwks(
    token: str, fetch_jwks: JwksFetcher, issuers: tuple[str, ...], audiences: tuple[str, ...]
) -> dict:
    try:
        kid = jwt.get_unverified_header(token)["kid"]
        keys = (await fetch_jwks())["keys"]
        key = next(k for k in keys if k.get("kid") == kid)
        # 대상 앱(aud)은 여러 값 중 하나일 수 있어서 아래에서 직접 확인한다.
        claims = jwt.decode(
            token, key, algorithms=["RS256"],
            options={"verify_aud": False, "verify_at_hash": False},
        )
    except (JWTError, KeyError, StopIteration) as exc:
        raise ProviderVerificationError("ID 토큰의 서명을 확인할 수 없습니다.") from exc
    if claims.get("iss") not in issuers or claims.get("aud") not in audiences:
        raise ProviderVerificationError("발급자 또는 대상 앱이 일치하지 않습니다.")
    return claims


def http_jwks_fetcher(http: httpx.AsyncClient, url: str, ttl_seconds: int = 3600) -> JwksFetcher:
    """제공자의 공개키 목록을 가져온다. ttl_seconds 동안은 메모리에 둔 값을 쓴다."""
    cache: dict = {"at": 0.0, "value": None}

    async def _fetch() -> dict:
        if cache["value"] is None or time.monotonic() - cache["at"] > ttl_seconds:
            response = await http.get(url)
            response.raise_for_status()
            cache["value"], cache["at"] = response.json(), time.monotonic()
        return cache["value"]

    return _fetch
