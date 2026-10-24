"""디스패처 조립과 루프 — 기동 때 asyncio 작업 하나가 돈다(설계 3.2). 테스트는 루프 대신 build_dispatcher(...).run_once()."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import NOTIFICATION_DAILY_CAP, SOLAPI_BALANCE_WARN_KRW
from core.database import session_scope
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.services.dispatcher import Dispatcher, DispatchReport, PeriodicState
from notification.app.services.dispatcher_wakeup import wait
from notification.dependencies.dispatcher_ports import dispatcher_ports
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_message_repository,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.clock import utc_now

logger = logging.getLogger("notification.dispatcher")

WAKE_SETTLE_SECONDS = 0.5      # 깨운 쪽(구독자)의 커밋이 먼저 닿게

_periodic = PeriodicState()    # 템플릿 상태·잔액을 본 시각 — 루프가 run_once 마다 새 Dispatcher 를 만들어도 프로세스에 하나


def reset_periodic() -> None:
    """테스트용 — 주기 시각을 비운다."""
    global _periodic
    _periodic = PeriodicState()


def build_dispatcher(
    db: AsyncSession, *, gateway: MessageGatewayPort | None = None, now: Callable[[], datetime] | None = None
) -> Dispatcher:
    ports = dispatcher_ports()
    messages = build_message_repository(db)
    return Dispatcher(
        queue=messages, channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db), messages=messages,
        gateway=gateway if gateway is not None else get_message_gateway(),
        shops=ports.shop_profile(db), directory=ports.customer_directory(db), ledger=ports.visit_ledger(db),
        commit=db.commit, rollback=db.rollback, now=now if now is not None else utc_now,
        daily_cap=NOTIFICATION_DAILY_CAP, balance_warn_krw=SOLAPI_BALANCE_WARN_KRW, periodic=_periodic,
    )


async def run_once() -> DispatchReport:
    async with session_scope() as db:
        return await build_dispatcher(db).run_once()


async def run_forever(stop: asyncio.Event, interval: float = 2.0) -> None:
    """stop 까지: interval 초마다 또는 깨우면 한 번 돈다. 한 번의 예외는 로그 뒤 다음 번으로."""
    while not stop.is_set():
        await wait(interval)
        if stop.is_set():
            return
        await asyncio.sleep(WAKE_SETTLE_SECONDS)
        if stop.is_set():
            return
        try:
            await run_once()
        except Exception as exc:
            logger.warning("디스패처 루프 한 번이 실패했습니다 (%s). 다음 번에 다시 돕니다.", type(exc).__name__)


def start_dispatcher() -> tuple[asyncio.Task, asyncio.Event]:
    """main.py 의 lifespan 이 부른다. 끝낼 때 stop.set() 과 wake() 뒤 task 를 기다린다."""
    stop = asyncio.Event()
    task = asyncio.create_task(run_forever(stop), name="notification-dispatcher")
    return task, stop
