from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.visit_events import VisitEvent


class DomainEventPort(ABC):
    """구현: core/observer(같은 프로세스·같은 세션의 동기 버스). 발행: visit. 구독: notification.
    구독자가 던지면 그대로 올라간다 — 발행한 유스케이스의 트랜잭션이 함께 실패한다(설계 5.1, N13)."""

    @abstractmethod
    async def publish(self, event: VisitEvent) -> None: ...
