from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.guardian import GuardianContext


class GuardianAccessPort(ABC):
    """구현: guardian. 사용: core/guardian_guard (보호자용 읽기의 가드) — `ShopAccessPort` 의 보호자 쪽 짝."""

    @abstractmethod
    async def resolve(self, user_id: int, link_id: int) -> GuardianContext:
        """그 계정의 살아 있는 연결인지 매 요청마다 DB 에서 본다. 아니면 GuardianAccessDeniedError —
        없는 연결·남의 연결·끝난 연결을 구분해 주지 않는다."""
