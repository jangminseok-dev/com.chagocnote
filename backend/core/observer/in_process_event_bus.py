"""Observer — 도메인 이벤트의 같은 프로세스·같은 세션 동기 버스(설계 3.1·5.1).

구독자 목록은 프로세스에 하나이고 진입점(main.py)이 기동 때 채운다. 이 모듈은 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import DbSession
from hub.app.dtos.visit_events import VisitEvent
from hub.app.ports.domain_event_port import DomainEventPort

Subscriber = Callable[[AsyncSession, VisitEvent], Awaitable[None]]

_subscribers: list[Subscriber] = []          # 진입점(main.py)이 기동 때 채운다


def subscribe(handler: Subscriber) -> None:
    """같은 함수를 두 번 넣지 않는다(이미 있으면 무시)."""
    if handler not in _subscribers:
        _subscribers.append(handler)


def unsubscribe(handler: Subscriber) -> None:
    """그 구독자만 뺀다(없으면 무시). 통합 테스트가 자기 구독자를 빼고 실제 구독자는 남기는 데 쓴다."""
    if handler in _subscribers:
        _subscribers.remove(handler)


def subscribers() -> tuple[Subscriber, ...]:
    return tuple(_subscribers)


def clear_subscribers() -> None:
    """단위 테스트용 — 실제 구독자까지 비우므로 통합 테스트는 unsubscribe 를 쓴다."""
    _subscribers.clear()


class InProcessEventBus(DomainEventPort):
    """등록된 순서대로, 같은 세션을 넘겨 동기로 부른다. 구독자가 없으면 아무 일도 없다."""

    def __init__(self, session: AsyncSession, handlers: Sequence[Subscriber]) -> None:
        self._session = session
        self._handlers = tuple(handlers)

    async def publish(self, event: VisitEvent) -> None:
        for handler in self._handlers:
            await handler(self._session, event)


def get_event_bus(db: DbSession) -> DomainEventPort:
    """FastAPI 프로바이더 — 요청의 세션에 묶인 버스. main.py 가 visit 의 자리에 꽂는다(작업 2)."""
    return InProcessEventBus(db, subscribers())
