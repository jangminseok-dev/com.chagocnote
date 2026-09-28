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


def _report_link_key() -> bytes:
    key = base64.b64decode(_m.require("REPORT_LINK_KEY_B64"))
    if len(key) < 32:
        raise RuntimeError("REPORT_LINK_KEY_B64 는 32바이트 이상의 키를 base64 로 적은 값이어야 합니다.")
    return key


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

# 미디어 객체 저장소(S3 호환 — 개발은 compose 의 MinIO). 서버는 내부 주소로 HEAD·DELETE 하고, 앱에 줄 URL 은
# 공개 주소로 서명한다(서명에 호스트가 들어간다). 운영은 S3 서울 리전 주소와 ap-northeast-2 를 넣는다.
S3_ENDPOINT_URL: str = _m.get("S3_ENDPOINT_URL", "http://minio:9000") or "http://minio:9000"
S3_PUBLIC_ENDPOINT_URL: str = _m.get("S3_PUBLIC_ENDPOINT_URL", "http://127.0.0.1:9010") or "http://127.0.0.1:9010"
S3_REGION: str = _m.get("S3_REGION", "us-east-1") or "us-east-1"
S3_BUCKET: str = _m.get("S3_BUCKET", "chagocnote-media") or "chagocnote-media"
S3_ACCESS_KEY: str = _m.get("S3_ACCESS_KEY", "") or ""
S3_SECRET_KEY: str = _m.get("S3_SECRET_KEY", "") or ""

# 미용 알림장(⑤). 링크의 토큰을 이 키로 서명한다 — 키를 바꾸면 보낸 링크가 모두 닫힌다.
REPORT_LINK_KEY: bytes = _report_link_key()
# 보호자가 여는 웹의 주소. 링크는 {REPORT_WEB_BASE_URL}/r/{토큰} 이다.
REPORT_WEB_BASE_URL: str = (_m.get("REPORT_WEB_BASE_URL", "") or "http://127.0.0.1:3010").rstrip("/")
# 웹 서버와 나누는 비밀값 — 맞을 때만 웹 서버가 알려 준 접속 주소로 횟수를 센다. 비어 있으면 믿지 않는다.
REPORT_WEB_SECRET: str = _m.get("REPORT_WEB_SECRET", "") or ""
