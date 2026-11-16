"""서류 청소(⑪ 설계 3.4) — 확인하지 않은 문진표의 답을 매장이 정한 보관 기간 뒤에 지운다.

새 손님의 답은 고객과 이어지지 않아 익명화로는 지워지지 않는다 — 이 작업이 유일한 길이다.
매장마다 `system_context` 로 자기 설정과 자기 표만 만진다. 로그에는 지운 수만 적는다.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from hub.app.dtos.shop_context import system_context


async def sweep_forms(
    answers: IntakeAnswerRepository, settings: FormSettingsRepository, now: datetime,
    commit: Callable[[], Awaitable[None]],
) -> int:
    """지운 답의 수. 매장마다 커밋한다 — 한 매장에서 실패해도 앞의 매장은 지워진 채다."""
    removed = 0
    for shop_id in await answers.shops_with_answers():
        ctx = system_context(shop_id)
        keep_days = (await settings.get(ctx)).intake_keep_days
        removed += await answers.delete_older(ctx, now - timedelta(days=keep_days))
        await commit()
    return removed
