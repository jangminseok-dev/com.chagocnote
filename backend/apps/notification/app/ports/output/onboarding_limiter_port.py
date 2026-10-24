from __future__ import annotations

from abc import ABC, abstractmethod


class OnboardingLimiterPort(ABC):
    """온보딩 요청의 횟수 제한(설계 9.4, N3·N4). 맞든 틀리든 시도마다 센다.

    저장소에 닿지 못하면 막지 않는다 — 업체 쪽 토큰 만료가 2차 방어다.
    """

    @abstractmethod
    async def allow(self, shop_id: int, action: str) -> bool:
        """요청 하나를 세고 창 안의 횟수가 한도 안이면 True. action 은 token·link·sender_verification·sender_confirm."""
