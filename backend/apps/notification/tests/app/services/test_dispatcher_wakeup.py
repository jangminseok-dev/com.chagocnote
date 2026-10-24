"""깨우기 — 같은 프로세스에서 줄이 생기면 루프가 기다림을 끊고 바로 돈다(설계 5.3-1)."""
import asyncio
import time

import pytest

from notification.app.services import dispatcher_wakeup


@pytest.fixture(autouse=True)
def fresh_event(monkeypatch):
    """asyncio.Event 는 처음 기다린 루프에 묶인다 — 테스트마다 루프가 새로 생기니 이벤트도 새로 둔다."""
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())


async def test_깨우면_기다림이_바로_끝나고_이벤트는_지워진다():
    dispatcher_wakeup.wake()
    started = time.monotonic()
    await dispatcher_wakeup.wait(5.0)
    assert time.monotonic() - started < 1.0
    assert not dispatcher_wakeup._event.is_set()


async def test_깨우지_않으면_시간이_지나야_끝난다():
    started = time.monotonic()
    await dispatcher_wakeup.wait(0.2)
    assert time.monotonic() - started >= 0.2


async def test_기다리는_중에_깨우면_그때_끝난다():
    waiter = asyncio.create_task(dispatcher_wakeup.wait(5.0))
    await asyncio.sleep(0.05)
    assert not waiter.done()
    dispatcher_wakeup.wake()
    await asyncio.wait_for(waiter, 1.0)
