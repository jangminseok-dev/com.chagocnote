"""서류 청소의 조립과 루프 — 기동 때 asyncio 작업 하나가 하루 한 번 돈다. 테스트는 루프 대신 sweep_forms_once()."""
from __future__ import annotations

import asyncio
import logging

from core.database import session_scope
from customer.app.services.form_sweeper import sweep_forms
from customer.dependencies.customer_wiring import (
    build_form_settings_repository, build_intake_answer_repository, utc_now,
)

logger = logging.getLogger("customer.form_sweeper")

SWEEP_INTERVAL_SECONDS = 24 * 60 * 60


async def sweep_forms_once() -> int:
    async with session_scope() as db:
        removed = await sweep_forms(
            build_intake_answer_repository(db), build_form_settings_repository(db), utc_now(), db.commit)
    logger.info("서류 청소: 문진표의 답 %d건을 지웠습니다.", removed)
    return removed


async def run_forever(stop: asyncio.Event, interval: float = SWEEP_INTERVAL_SECONDS) -> None:
    """stop 까지 interval 초마다 한 번 돈다. 기동하자마자 한 번 돈다. 한 번의 예외는 로그 뒤 다음 번으로."""
    while not stop.is_set():
        try:
            await sweep_forms_once()
        except Exception as exc:      # noqa: BLE001 — 루프를 죽이지 않는다. 예외의 형 이름만 적는다(글이 들 수 있다).
            logger.warning("서류 청소에 실패했습니다: %s", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass


def start_form_sweeper() -> tuple[asyncio.Task, asyncio.Event]:
    stop = asyncio.Event()
    return asyncio.create_task(run_forever(stop)), stop
