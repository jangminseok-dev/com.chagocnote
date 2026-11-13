from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.guardian import ReportLinkTarget


class ReportLinkPort(ABC):
    """구현: visit. 사용: guardian (알림장 링크로 고객 카드와 계정을 잇는다)."""

    @abstractmethod
    async def resolve(self, token: str | None) -> ReportLinkTarget | None:
        """토큰의 서명을 확인하고 그 알림장의 매장·고객과 열려 있는지를 준다. 토큰이 없거나 우리가 만든 것이
        아니면 None. 토큰을 로그에 남기지 않는다."""
