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
from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.visit_events import VisitReserved
from hub.app.ports.domain_event_port import DomainEventPort

NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clean_subscribers():
    """비우고 돌린 뒤 실제 구독자(main.py 가 import 때 꽂은 것)를 되살린다 — 같은 프로세스의 뒤 테스트가 잃지 않게."""
    kept = subscribers()
    clear_subscribers()
    yield
    clear_subscribers()
    for handler in kept:
        subscribe(handler)


def _event() -> VisitReserved:
    ctx = ShopContext(shop_id=1, member_id=11, role="owner", permissions=frozenset())
    return VisitReserved(ctx=ctx, visit_id=7, customer_id=1, pet_id=101, starts_at=NOW, occurred_at=NOW)


def _recorder(name, log):
    async def handler(session, event):
        log.append((name, session, event))
    return handler


async def test_구독자는_등록_순서대로_같은_세션과_이벤트를_받는다():
    log, session, event = [], object(), _event()
    bus = InProcessEventBus(session, [_recorder("first", log), _recorder("second", log)])
    await bus.publish(event)
    assert log == [("first", session, event), ("second", session, event)]


async def test_구독자가_없으면_publish_는_아무_일도_하지_않는다():
    await InProcessEventBus(object(), []).publish(_event())


async def test_구독자가_던지면_그대로_올라가고_뒤_구독자는_불리지_않는다():
    """N13 — 구독자 예외는 발행한 유스케이스의 트랜잭션을 함께 실패시킨다(의도)."""
    log = []

    async def failing(session, event):
        raise RuntimeError("구독자 실패")

    bus = InProcessEventBus(object(), [failing, _recorder("after", log)])
    with pytest.raises(RuntimeError):
        await bus.publish(_event())
    assert log == []


async def test_같은_함수를_두_번_subscribe_해도_한_번만_등록된다():
    handler = _recorder("once", [])
    subscribe(handler)
    subscribe(handler)
    assert subscribers() == (handler,)


async def test_unsubscribe_는_그_구독자만_빼고_없는_것은_무시한다():
    first, second = _recorder("first", []), _recorder("second", [])
    subscribe(first)
    subscribe(second)
    unsubscribe(first)
    unsubscribe(first)
    assert subscribers() == (second,)


async def test_get_event_bus_는_넘긴_세션에_묶인_버스를_준다():
    log, session, event = [], object(), _event()
    subscribe(_recorder("registered", log))
    bus = get_event_bus(session)
    assert isinstance(bus, DomainEventPort)
    await bus.publish(event)
    assert log == [("registered", session, event)]
