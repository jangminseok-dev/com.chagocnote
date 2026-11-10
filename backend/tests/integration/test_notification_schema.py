"""notification 네 표의 실제 CHECK·부분 색인이 도메인 튜플과 같은 값을 같은 순서로 말하는지 — 실제 DB 에서 읽는다.

마이그레이션 0011 은 상태 목록을 글자로 적는다. tests/test_schema_drift.py 는 CHECK 와 부분 색인의 WHERE 를 비교하지
않으므로, 도메인에 값을 더하고 마이그레이션을 잊으면 여기서 걸린다.
"""
import re

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from notification.domain.value_objects.channel_status import CHANNEL_STATUSES
from notification.domain.value_objects.message_kind import KINDS
from notification.domain.value_objects.message_status import (
    CANCEL_REASONS,
    CHANNELS_USED,
    ERROR_KINDS,
    PENDING_STATUSES,
    STATUSES,
)
from notification.domain.value_objects.template_status import TEMPLATE_STATUSES

pytestmark = pytest.mark.integration

_QUOTED = re.compile(r"'([a-z_]+)'")


async def _constraint_def(engine, name: str) -> str:
    async with engine.connect() as conn:
        return (await conn.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"), {"name": name}
        )).scalar_one()


async def _index_predicate(engine, name: str) -> str:
    async with engine.connect() as conn:
        return (await conn.execute(text(
            "SELECT pg_get_expr(i.indpred, i.indrelid) FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
            "WHERE c.relname = :name"), {"name": name}
        )).scalar_one()


@pytest.mark.parametrize(("name", "values"), [
    ("ck_notification_channels_status", CHANNEL_STATUSES),
    ("ck_notification_templates_kind", KINDS),
    ("ck_notification_templates_status", TEMPLATE_STATUSES),
    ("ck_notification_messages_kind", KINDS),
    ("ck_notification_messages_status", STATUSES),
    ("ck_notification_messages_canceled_reason", CANCEL_REASONS),
    ("ck_notification_messages_channel_used", CHANNELS_USED),
    ("ck_notification_messages_error_kind", ERROR_KINDS),
])
async def test_CHECK_는_도메인_튜플의_값을_같은_순서로_담는다(db_engine, name, values):
    assert _QUOTED.findall(await _constraint_def(db_engine, name)) == list(values)


async def test_대기_줄_부분_유일_색인은_대기_상태만_담는다(db_engine):
    predicate = await _index_predicate(db_engine, "uq_notification_messages_pending")
    assert _QUOTED.findall(predicate) == [s for s in STATUSES if s in PENDING_STATUSES]


async def test_취소_이유는_취소_상태에만_있다(db_engine):
    assert _QUOTED.findall(await _constraint_def(db_engine, "ck_notification_messages_canceled")) == ["canceled"]


async def test_문자_대체는_발신번호_인증이_있어야_켤_수_있다(db_engine):
    definition = await _constraint_def(db_engine, "ck_notification_channels_fallback")
    assert "sms_fallback_enabled" in definition and "sender_number_verified_at IS NOT NULL" in definition


async def test_템플릿_대기_칸은_둘이_함께_있거나_함께_없다(db_engine):
    definition = await _constraint_def(db_engine, "ck_notification_templates_pending_pair")
    assert "pending_text_version" in definition and "pending_provider_template_id" in definition
    insert = text(
        "INSERT INTO notification_templates (shop_id, kind, text_version, provider_template_id, status, requested_at, "
        "pending_text_version, pending_provider_template_id) VALUES (1, 'confirm', 1, 'TP', 'approved', now(), :v, :p)")
    for half in ({"v": 2, "p": None}, {"v": None, "p": "TP2"}):
        with pytest.raises(IntegrityError):
            async with db_engine.begin() as conn:
                await conn.execute(insert, half)
