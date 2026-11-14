"""Observer — 도메인 이벤트의 같은 프로세스·같은 세션 동기 버스(설계 3.1·5.1).

구독자 목록은 프로세스에 하나이고 진입점(main.py)이 기동 때 채운다. 구독자는 받을 이벤트의 형과 함께 등록한다 —
버스는 그 형(과 하위 형)의 이벤트만 넘긴다. 이 모듈은 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import DbSession
from hub.app.ports.domain_event_port import DomainEvent, DomainEventPort

Subscriber = Callable[[AsyncSession, Any], Awaitable[None]]   # 둘째 인자는 등록한 형의 이벤트다
Subscription = tuple[Subscriber, type]

_subscribers: list[Subscription] = []          # 진입점(main.py)이 기동 때 채운다


def subscribe(handler: Subscriber, event_type: type) -> None:
    """handler 는 event_type(과 그 하위 형)의 이벤트만 받는다. 같은 짝을 두 번 넣지 않는다(이미 있으면 무시)."""
    if (handler, event_type) not in _subscribers:
        _subscribers.append((handler, event_type))


def unsubscribe(handler: Subscriber) -> None:
    """그 구독자의 등록을 모두 뺀다(없으면 무시). 통합 테스트가 자기 구독자를 빼고 실제 구독자는 남기는 데 쓴다."""
    _subscribers[:] = [pair for pair in _subscribers if pair[0] is not handler]


def subscribers() -> tuple[Subscription, ...]:
    return tuple(_subscribers)


def clear_subscribers() -> None:
    """단위 테스트용 — 실제 구독자까지 비우므로 통합 테스트는 unsubscribe 를 쓴다."""
    _subscribers.clear()


class InProcessEventBus(DomainEventPort):
    """등록된 순서대로, 같은 세션을 넘겨 동기로 부른다. 그 형의 구독자가 없으면 아무 일도 없다."""

    def __init__(self, session: AsyncSession, subscriptions: Sequence[Subscription]) -> None:
        self._session = session
        self._subscriptions = tuple(subscriptions)

    async def publish(self, event: DomainEvent) -> None:
        for handler, event_type in self._subscriptions:
            if isinstance(event, event_type):
                await handler(self._session, event)


def get_event_bus(db: DbSession) -> DomainEventPort:
    """FastAPI 프로바이더 — 요청의 세션에 묶인 버스. main.py 가 발행하는 스포크의 자리에 꽂는다."""
    return InProcessEventBus(db, subscribers())
