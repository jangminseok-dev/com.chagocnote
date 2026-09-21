"""구글·Apple 전략이 함께 쓰는 ID 토큰 서명 검증."""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import httpx
from jose import JWTError, jwt

from auth.domain.errors import ProviderVerificationError

JwksFetcher = Callable[[], Awaitable[dict]]


def _find_key(jwks: dict, kid: str) -> dict | None:
    return next((k for k in jwks["keys"] if k.get("kid") == kid), None)


async def verify_with_jwks(
    token: str, fetch_jwks: JwksFetcher, issuers: tuple[str, ...], audiences: tuple[str, ...],
    refetch_jwks: JwksFetcher | None = None,
) -> dict:
    try:
        kid = jwt.get_unverified_header(token)["kid"]
        key = _find_key(await fetch_jwks(), kid)
        if key is None and refetch_jwks is not None:
            # 제공자가 서명 키를 바꿨을 수 있다. 캐시를 건너뛰고 한 번만 다시 받아 본다.
            key = _find_key(await refetch_jwks(), kid)
        if key is None:
            raise KeyError(kid)
        # 대상 앱(aud)은 여러 값 중 하나일 수 있어서 아래에서 직접 확인한다.
        claims = jwt.decode(
            token, key, algorithms=["RS256"],
            options={"verify_aud": False, "verify_at_hash": False},
        )
    except (JWTError, KeyError) as exc:
        raise ProviderVerificationError("ID 토큰의 서명을 확인할 수 없습니다.") from exc
    if claims.get("iss") not in issuers or claims.get("aud") not in audiences:
        raise ProviderVerificationError("발급자 또는 대상 앱이 일치하지 않습니다.")
    if not claims.get("sub"):
        raise ProviderVerificationError("ID 토큰에 사용자 식별자가 없습니다.")
    return claims


def http_jwks_fetchers(
    http: httpx.AsyncClient, url: str, ttl_seconds: int = 3600, min_refetch_seconds: int = 60,
    now: Callable[[], float] = time.monotonic,
) -> tuple[JwksFetcher, JwksFetcher]:
    """(캐시를 쓰는 조회, 강제 재조회)를 돌려준다. 둘은 같은 캐시를 본다.

    강제 재조회는 min_refetch_seconds 에 한 번만 제공자를 부른다. 모르는 kid 를 쏟아붓는 요청이
    제공자를 계속 두드리게 하지 않으려는 것이다. 실패도 같은 간격만큼 기억한다(음성 캐시) — 그렇지
    않으면 제공자가 죽어 있는 동안은 매 요청이 다시 시도해 같은 문제가 생긴다.
    """
    cache: dict = {"at": 0.0, "value": None, "failed_at": None}

    async def _load() -> dict:
        if cache["failed_at"] is not None and now() - cache["failed_at"] < min_refetch_seconds:
            raise ProviderVerificationError("제공자의 공개키를 가져올 수 없습니다.")
        try:
            response = await http.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            cache["failed_at"] = now()
            raise ProviderVerificationError("제공자의 공개키를 가져올 수 없습니다.") from exc
        cache["value"], cache["at"] = response.json(), now()
        cache["failed_at"] = None
        return cache["value"]

    async def fetch() -> dict:
        if cache["value"] is None or now() - cache["at"] > ttl_seconds:
            return await _load()
        return cache["value"]

    async def refetch() -> dict:
        if cache["value"] is not None and now() - cache["at"] < min_refetch_seconds:
            return cache["value"]
        return await _load()

    return fetch, refetch
