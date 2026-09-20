import secrets


def new_refresh_token() -> str:
    """추측할 수 없는 불투명 문자열. JWT 가 아니다 — 서버 저장소에 있어야만 유효하다."""
    return secrets.token_urlsafe(48)
