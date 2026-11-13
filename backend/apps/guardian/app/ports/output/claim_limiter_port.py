from __future__ import annotations

from abc import ABC, abstractmethod


class ClaimLimiterPort(ABC):
    """잇기 시도의 횟수 제한 — 계정당 시간당 10회(⑦ 설계 G4). 맞든 틀리든 시도마다 센다.

    저장소에 닿지 못하면 막지 않는다 — 토큰의 서명이 1차 방어다.
    """

    @abstractmethod
    async def allow(self, user_id: int) -> bool:
        """시도 하나를 세고 창 안의 횟수가 한도 안이면 True."""
