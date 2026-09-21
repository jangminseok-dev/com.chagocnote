import secrets


def new_refresh_token(user_id: int) -> str:
    """추측할 수 없는 불투명 문자열. JWT 가 아니다 — 서버 저장소에 있어야만 유효하다.

    앞에 유저 ID 를 붙인다. 서버가 토큰만 보고 그 유저의 세대 키를 알 수 있어야
    Redis 스크립트의 모든 키를 미리 넘길 수 있다. 유저 ID 는 액세스 토큰에도 있는 값이라 숨길 것이 아니다.
    """
    return f"{user_id}.{secrets.token_urlsafe(48)}"


def refresh_token_user_id(token: str) -> int | None:
    head, dot, _ = token.partition(".")
    return int(head) if dot and head.isascii() and head.isdigit() else None
