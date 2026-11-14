"""API 프로세스의 lifespan — 기동하면 디스패처 작업이 돌고, 끝나면 멈춘다. DB 엔진·Redis 는 가짜, 게이트웨이는 Fake."""
import asyncio

import pytest

import main
from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.services import dispatcher_wakeup
from notification.app.services.dispatcher import DispatchReport
from notification.dependencies import dispatcher_provider as provider
from search.app.services import indexer_wakeup
from search.app.services.indexer import IndexReport
from search.dependencies import indexer_provider


@pytest.fixture(autouse=True)
def fresh_event(monkeypatch):
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())
    monkeypatch.setattr(indexer_wakeup, "_event", asyncio.Event())


async def _index_nothing() -> IndexReport:
    return IndexReport()


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
    monkeypatch.setattr(indexer_provider, "run_once", _index_nothing)

    async with main.lifespan(main.app):
        [task] = _dispatcher_tasks()
        dispatcher_wakeup.wake()
        await asyncio.sleep(0.8)
        assert runs == 1
    assert task.done() and _dispatcher_tasks() == []


def _indexer_tasks() -> list[asyncio.Task]:
    return [t for t in asyncio.all_tasks() if t.get_name() == "search-indexer"]


async def test_lifespan_은_검색_색인기를_시작하고_끝나면_멈춘다(monkeypatch):
    runs = 0

    async def run_once() -> IndexReport:
        nonlocal runs
        runs += 1
        return IndexReport()

    async def dispatch_once() -> DispatchReport:
        return DispatchReport()

    async def nothing() -> None:
        return None

    monkeypatch.setattr(main, "init_engine", lambda: None)
    monkeypatch.setattr(main, "dispose_engine", nothing)
    monkeypatch.setattr(main, "dispose_redis", nothing)
    monkeypatch.setattr(main, "get_message_gateway", FakeGateway)
    monkeypatch.setattr(provider, "run_once", dispatch_once)
    monkeypatch.setattr(indexer_provider, "run_once", run_once)

    async with main.lifespan(main.app):
        [task] = _indexer_tasks()
        indexer_wakeup.wake()
        await asyncio.sleep(0.8)
        assert runs == 1
    assert task.done() and _indexer_tasks() == []


async def test_색인기_루프는_한_번이_던져도_계속_돈다(monkeypatch, caplog):
    calls = 0

    async def run_once() -> IndexReport:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("귀를 만지면 무는 아이")
        return IndexReport()

    monkeypatch.setattr(indexer_provider, "run_once", run_once)
    monkeypatch.setattr(indexer_provider, "WAKE_SETTLE_SECONDS", 0)
    stop = asyncio.Event()
    task = asyncio.create_task(indexer_provider.run_forever(stop, interval=0.01))
    await asyncio.sleep(0.2)
    stop.set()
    indexer_wakeup.wake()
    await task
    assert calls >= 2
    assert "RuntimeError" in caplog.text and "귀를 만지면" not in caplog.text


async def test_색인기_루프는_줄이_가득_집히면_쉬지_않고_이어_돈다(monkeypatch):
    """처음 채울 때처럼 줄이 많으면 한 묶음(20)씩 2초를 기다리지 않는다."""
    reports = [IndexReport(claimed=20, indexed=20), IndexReport(claimed=20, indexed=20), IndexReport(claimed=3, indexed=3)]
    calls = 0

    async def run_once() -> IndexReport:
        nonlocal calls
        calls += 1
        return reports.pop(0) if reports else IndexReport()

    monkeypatch.setattr(indexer_provider, "run_once", run_once)
    monkeypatch.setattr(indexer_provider, "WAKE_SETTLE_SECONDS", 0)
    stop = asyncio.Event()
    task = asyncio.create_task(indexer_provider.run_forever(stop, interval=30))
    indexer_wakeup.wake()
    await asyncio.sleep(0.2)
    assert calls == 3                    # 30초 간격을 기다리지 않고 셋을 이어 돌았다
    stop.set()
    indexer_wakeup.wake()
    await task
