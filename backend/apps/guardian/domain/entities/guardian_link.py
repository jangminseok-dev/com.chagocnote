from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# 무엇으로 본인을 확인했나 — 지금은 받은 알림장 링크뿐이다. 전화번호 확인을 더하면 값이 는다(⑦ 설계 2절).
VERIFIED_BY = ("report_link",)
# 누가 끝냈나 — 보호자, 매장, 계정 탈퇴, 고객 익명화.
ENDED_BY = ("guardian", "shop", "withdrawn", "anonymized")


@dataclass(frozen=True)
class GuardianLink:
    """보호자 계정과 매장의 고객 카드를 잇는 연결 한 줄(⑦ 설계 4.2). 전화번호·이름은 담지 않는다.

    고객 카드 하나에 살아 있는 연결은 하나다. 끝난 연결의 줄은 남긴다 — 누가 언제 이었고 끊었는지.
    """

    id: int
    user_id: int
    shop_id: int
    customer_id: int
    verified_by: str
    created_at: datetime
    ended_at: datetime | None
    ended_by: str | None

    @property
    def is_live(self) -> bool:
        return self.ended_at is None
