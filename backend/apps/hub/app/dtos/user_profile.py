from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserProfile:
    """다른 스포크에 보여 줘도 되는 유저 정보. 전화번호와 로그인 수단은 넣지 않는다."""

    user_id: int
    display_name: str
    profile_image_url: str | None
