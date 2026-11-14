from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.dtos.visit_events import VisitEvent

# 버스에 실리는 이벤트의 형. 새 이벤트를 만들면 여기에 더한다.
DomainEvent = VisitEvent | SearchSourceChanged


class DomainEventPort(ABC):
    """구현: core/observer(같은 프로세스·같은 세션의 동기 버스). 발행: visit, customer. 구독: notification
    (`VisitEvent`), search(`SearchSourceChanged`) — 구독자는 자기가 고른 형의 이벤트만 받는다.
    구독자가 던지면 그대로 올라간다 — 발행한 유스케이스의 트랜잭션이 함께 실패한다(설계 5.1, N13)."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...
