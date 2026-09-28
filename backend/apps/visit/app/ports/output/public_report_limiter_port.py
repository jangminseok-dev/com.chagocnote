from __future__ import annotations

from abc import ABC, abstractmethod


class PublicReportLimiterPort(ABC):
    """공개 조회의 횟수 제한(설계 7.1). client 는 접속 주소다.

    저장소에 닿지 못하면 막지 않는다 — 1차 방어는 토큰의 크기다.
    """

    @abstractmethod
    async def allow(self, client: str) -> bool:
        """요청 하나를 세고 받아도 되는지 알려 준다. 1분에 60번을 넘었거나 10분 안의 실패가 20번이면 False."""

    @abstractmethod
    async def note_miss(self, client: str) -> None:
        """없는 알림장을 찾은 요청(404)을 하나 센다."""
