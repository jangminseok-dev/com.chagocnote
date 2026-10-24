"""API 프로세스의 lifespan — 기동하면 디스패처 작업이 돌고, 끝나면 멈춘다. DB 엔진·Redis 는 가짜, 게이트웨이는 Fake."""
import asyncio

import pytest

import main
from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.services import dispatcher_wakeup
from notification.app.services.dispatcher import DispatchReport
from notification.dependencies import dispatcher_provider as provider


@pytest.fixture(autouse=True)
def fresh_event(monkeypatch):
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())


def _dispatcher_tasks() -> list[asyncio.Task]:
    return [t for t in asyncio.all_tasks() if t.get_name() == "notification-dispatcher"]


async def test_lifespan_은_디스패처를_시작하고_끝나면_멈춘다(monkeypatch):
    runs = 0

    async def run_once() -> DispatchReport:
        nonlocal runs
        runs += 1
        return DispatchReport()

    async def nothing() -> None:
        return None

    monkeypatch.setattr(main, "init_engine", lambda: None)
    monkeypatch.setattr(main, "dispose_engine", nothing)
    monkeypatch.setattr(main, "dispose_redis", nothing)
    monkeypatch.setattr(main, "get_message_gateway", FakeGateway)
    monkeypatch.setattr(provider, "run_once", run_once)

    async with main.lifespan(main.app):
        [task] = _dispatcher_tasks()
        dispatcher_wakeup.wake()
        await asyncio.sleep(0.8)
        assert runs == 1
    assert task.done() and _dispatcher_tasks() == []
