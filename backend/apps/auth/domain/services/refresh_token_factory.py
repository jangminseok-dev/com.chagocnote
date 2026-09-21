import secrets


def new_refresh_token(user_id: int) -> str:
    """추측할 수 없는 불투명 문자열. JWT 가 아니다 — 서버 저장소에 있어야만 유효하다.

    앞에 유저 ID 를 붙인다. 서버가 토큰만 보고 그 유저의 세대 키를 알 수 있어야
    Redis 스크립트의 모든 키를 미리 넘길 수 있다. 유저 ID 는 액세스 토큰에도 있는 값이라 숨길 것이 아니다.
    """
    return f"{user_id}.{secrets.token_urlsafe(48)}"


def refresh_token_user_id(token: str) -> int | None:
    head, dot, _ = token.partition(".")
    # 유저 ID 는 DB 의 정수 PK 라 19자리(64비트 부호 있는 정수 최대치)를 넘지 않는다.
    # 공격자가 아주 긴 숫자열을 보내면 int() 가 ValueError 를 낸다(3.11+ 는 4300자리로 제한).
    if not (dot and head.isascii() and 1 <= len(head) <= 19 and head.isdigit()):
        return None
    return int(head)
