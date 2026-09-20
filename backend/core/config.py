"""런타임 상수 — 앱 코드는 비밀값 관리자를 직접 부르지 않고 여기 상수만 쓴다.

JWT 개인키는 여기 두지 않는다 (core/auth_config.py). API 프로세스는 토큰을 발급할 수 없어야 한다.
"""
from __future__ import annotations

import base64

from core.singleton.secret_manager import get_secret_manager

_m = get_secret_manager()


def _b64_pem(name: str) -> str:
    raw = _m.get(name, "")
    return base64.b64decode(raw).decode() if raw else ""


# 보안 게이트 기본값은 닫힘이어야 한다 — 운영 배포가 APP_ENV 설정을 빠뜨려도 dev 전용 로그인 제공자가 열리면 안 된다.
APP_ENV: str = _m.get("APP_ENV", "prod") or "prod"
DATABASE_URL: str = _m.require("DATABASE_URL")
REDIS_URL: str = _m.get("REDIS_URL", "redis://redis:6379/0") or "redis://redis:6379/0"
JWT_PUBLIC_KEY: str = base64.b64decode(_m.require("JWT_PUBLIC_KEY_B64")).decode()

ACCESS_TOKEN_TTL_SECONDS = 15 * 60
REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60

KAKAO_APP_ID: str = _m.get("KAKAO_APP_ID", "") or ""
GOOGLE_CLIENT_IDS: tuple[str, ...] = tuple(
    v for v in (_m.get("GOOGLE_CLIENT_ID_IOS", ""), _m.get("GOOGLE_CLIENT_ID_ANDROID", "")) if v
)
APPLE_BUNDLE_ID: str = _m.get("APPLE_BUNDLE_ID", "") or ""
APPLE_TEAM_ID: str = _m.get("APPLE_TEAM_ID", "") or ""
APPLE_KEY_ID: str = _m.get("APPLE_KEY_ID", "") or ""
APPLE_PRIVATE_KEY: str = _b64_pem("APPLE_PRIVATE_KEY_B64")
IDENTITY_TOKEN_ENC_KEY: str = _m.require("IDENTITY_TOKEN_ENC_KEY")
