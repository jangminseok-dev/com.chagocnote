"""core/observer 의 동기 버스 — 등록 순서, 같은 세션, 예외 전파, 중복 등록, 프로바이더."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.observer.in_process_event_bus import (
    InProcessEventBus,
    clear_subscribers,
    get_event_bus,
    subscribe,
    subscribers,
    unsubscribe,
)
from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.visit_events import VisitEvent, VisitReserved
from hub.app.ports.domain_event_port import DomainEventPort

NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clean_subscribers():
    """비우고 돌린 뒤 실제 구독자(main.py 가 import 때 꽂은 것)를 되살린다 — 같은 프로세스의 뒤 테스트가 잃지 않게."""
    kept = subscribers()
    clear_subscribers()
    yield
    clear_subscribers()
    for handler, event_type in kept:
        subscribe(handler, event_type)


def _event() -> VisitReserved:
    ctx = ShopContext(shop_id=1, member_id=11, role="owner", permissions=frozenset())
    return VisitReserved(ctx=ctx, visit_id=7, customer_id=1, pet_id=101, starts_at=NOW, occurred_at=NOW)


def _recorder(name, log):
    async def handler(session, event):
        log.append((name, session, event))
    return handler


async def test_구독자는_등록_순서대로_같은_세션과_이벤트를_받는다():
    log, session, event = [], object(), _event()
    bus = InProcessEventBus(session, [(_recorder("first", log), VisitEvent), (_recorder("second", log), VisitEvent)])
    await bus.publish(event)
    assert log == [("first", session, event), ("second", session, event)]


async def test_구독자가_없으면_publish_는_아무_일도_하지_않는다():
    await InProcessEventBus(object(), []).publish(_event())


async def test_구독자가_던지면_그대로_올라가고_뒤_구독자는_불리지_않는다():
    """N13 — 구독자 예외는 발행한 유스케이스의 트랜잭션을 함께 실패시킨다(의도)."""
    log = []

    async def failing(session, event):
        raise RuntimeError("구독자 실패")

    bus = InProcessEventBus(object(), [(failing, VisitEvent), (_recorder("after", log), VisitEvent)])
    with pytest.raises(RuntimeError):
        await bus.publish(_event())
    assert log == []


async def test_같은_함수를_두_번_subscribe_해도_한_번만_등록된다():
    handler = _recorder("once", [])
    subscribe(handler, VisitEvent)
    subscribe(handler, VisitEvent)
    assert subscribers() == ((handler, VisitEvent),)


async def test_unsubscribe_는_그_구독자만_빼고_없는_것은_무시한다():
    first, second = _recorder("first", []), _recorder("second", [])
    subscribe(first, VisitEvent)
    subscribe(second, VisitEvent)
    unsubscribe(first)
    unsubscribe(first)
    assert subscribers() == ((second, VisitEvent),)


async def test_get_event_bus_는_넘긴_세션에_묶인_버스를_준다():
    log, session, event = [], object(), _event()
    subscribe(_recorder("registered", log), VisitEvent)
    bus = get_event_bus(session)
    assert isinstance(bus, DomainEventPort)
    await bus.publish(event)
    assert log == [("registered", session, event)]


def _changed() -> SearchSourceChanged:
    ctx = ShopContext(shop_id=1, member_id=11, role="owner", permissions=frozenset())
    return SearchSourceChanged(ctx=ctx, scope="visit", ref_id=7)


async def test_구독자는_자기가_고른_형의_이벤트만_받는다():
    """알림 구독자가 검색 이벤트마다 불리지 않는다(그 반대도) — 형이 다른 이벤트는 건너뛴다."""
    log, session = [], object()
    bus = InProcessEventBus(session, [
        (_recorder("visit", log), VisitEvent), (_recorder("search", log), SearchSourceChanged),
    ])
    visit_event, changed = _event(), _changed()
    await bus.publish(visit_event)
    await bus.publish(changed)
    assert log == [("visit", session, visit_event), ("search", session, changed)]


async def test_하위_형의_이벤트는_바탕_형의_구독자가_받는다():
    log = []
    await InProcessEventBus(object(), [(_recorder("visit", log), VisitEvent)]).publish(_event())
    assert [name for name, _, _ in log] == ["visit"]


async def test_같은_함수를_다른_형으로_등록하면_둘_다_남는다():
    handler = _recorder("both", [])
    subscribe(handler, VisitEvent)
    subscribe(handler, SearchSourceChanged)
    assert subscribers() == ((handler, VisitEvent), (handler, SearchSourceChanged))
    unsubscribe(handler)
    assert subscribers() == ()


def test_system_context_는_권한이_비어_있고_멤버가_없다():
    from hub.app.dtos.shop_context import system_context

    made = system_context(7, "Asia/Tokyo")
    assert (made.shop_id, made.member_id, made.role, made.permissions, made.timezone) == (
        7, 0, "system", frozenset(), "Asia/Tokyo")
    assert system_context(7).timezone == "Asia/Seoul"
