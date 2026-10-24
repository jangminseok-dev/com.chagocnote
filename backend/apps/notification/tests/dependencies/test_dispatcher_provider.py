"""디스패처 조립과 루프 — 허브 포트 공장 자리, build_dispatcher 의 게이트웨이·시계 주입, run_forever 의 깨우기·정지·예외."""
import asyncio
import logging

import pytest

from notification.app.services import dispatcher_wakeup
from notification.app.services.dispatcher import DispatchReport, Dispatcher
from notification.dependencies import dispatcher_ports as ports_module
from notification.dependencies import dispatcher_provider as provider
from notification.dependencies.dispatcher_ports import DispatcherPorts, configure_dispatcher_ports, dispatcher_ports
from notification.tests.helpers.builders import kst
from notification.tests.helpers.fakes import FakeDirectory, FakeLedger, FakeShopProfile, SpyGateway

NOW = kst(10, 14, 11)


@pytest.fixture(autouse=True)
def fresh_event(monkeypatch):
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())


@pytest.fixture
def stub_ports(monkeypatch):
    """main.py 가 꽂은 실제 프로바이더 대신 스텁 공장 — 세션 없이 조립만 본다."""
    monkeypatch.setattr(ports_module, "_ports", None)
    ports = DispatcherPorts(shop_profile=lambda db: FakeShopProfile(), customer_directory=lambda db: FakeDirectory(),
                            visit_ledger=lambda db: FakeLedger())
    configure_dispatcher_ports(ports)
    return ports


def test_허브_포트_자리가_비어_있으면_RuntimeError(monkeypatch):
    monkeypatch.setattr(ports_module, "_ports", None)
    with pytest.raises(RuntimeError, match="진입점에서 조립"):
        dispatcher_ports()


def test_꽂은_공장을_돌려준다(stub_ports):
    assert dispatcher_ports() is stub_ports


class _Session:
    """저장소가 세션을 들고만 있으니 commit 만 있으면 된다."""

    async def commit(self) -> None:
        return None


def test_build_dispatcher_는_넘긴_게이트웨이와_시계를_쓰고_저장소는_세션으로_만든다(stub_ports):
    gateway, session = SpyGateway(), _Session()
    dispatcher = provider.build_dispatcher(session, gateway=gateway, now=lambda: NOW)
    assert isinstance(dispatcher, Dispatcher)
    assert dispatcher._gateway is gateway and dispatcher._now() == NOW
    assert dispatcher._commit == session.commit
    assert (dispatcher._daily_cap, dispatcher._balance_warn_krw) == (provider.NOTIFICATION_DAILY_CAP,
                                                                     provider.SOLAPI_BALANCE_WARN_KRW)


def test_build_dispatcher_는_기본으로_프로세스의_게이트웨이를_쓴다(stub_ports, monkeypatch):
    gateway = SpyGateway()
    monkeypatch.setattr(provider, "get_message_gateway", lambda: gateway)
    assert provider.build_dispatcher(_Session())._gateway is gateway


async def test_루프는_깨우면_반_초_뒤에_한_번_돌고_정지하면_끝난다(monkeypatch):
    runs: list[float] = []
    loop = asyncio.get_running_loop()

    async def run_once() -> DispatchReport:
        runs.append(loop.time())
        return DispatchReport()

    monkeypatch.setattr(provider, "run_once", run_once)
    stop = asyncio.Event()
    task = asyncio.create_task(provider.run_forever(stop, interval=30.0))
    await asyncio.sleep(0.1)
    assert runs == []
    woke = loop.time()
    dispatcher_wakeup.wake()
    await asyncio.sleep(0.8)
    assert len(runs) == 1 and 0.4 <= runs[0] - woke < 0.8

    stop.set()
    dispatcher_wakeup.wake()
    await asyncio.wait_for(task, 1.0)
    assert len(runs) == 1


async def test_루프는_run_once_의_예외를_로그에_남기고_계속_돈다(monkeypatch, caplog):
    calls = 0

    async def run_once() -> DispatchReport:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("DB 가 잠깐 죽었다")
        return DispatchReport()

    monkeypatch.setattr(provider, "run_once", run_once)
    stop = asyncio.Event()
    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        task = asyncio.create_task(provider.run_forever(stop, interval=0.05))
        await asyncio.sleep(1.4)
        stop.set()
        dispatcher_wakeup.wake()
        await asyncio.wait_for(task, 1.0)

    assert calls >= 2
    assert any("RuntimeError" in record.getMessage() for record in caplog.records)


async def test_start_dispatcher_는_이름_있는_작업과_정지_이벤트를_돌려준다(monkeypatch):
    async def run_once() -> DispatchReport:
        return DispatchReport()

    monkeypatch.setattr(provider, "run_once", run_once)
    task, stop = provider.start_dispatcher()
    assert task.get_name() == "notification-dispatcher" and not task.done()
    stop.set()
    dispatcher_wakeup.wake()
    await asyncio.wait_for(task, 1.0)
