"""visits 표의 실제 CHECK·부분 색인이 도메인 상태 표(visit_status)와 같은 상태를 말하는지 — 실제 DB 에서 읽는다.

tests/test_schema_drift.py 의 compare_metadata 는 CHECK 와 부분 색인의 WHERE 를 비교하지 않는다. 표에 상태를 더하고
마이그레이션을 잊으면 ORM 은 새 상태를 알지만 DB CHECK 는 옛것이라 첫 INSERT 가 500 이 된다 — 여기서 미리 걸린다.
"""
import re

import pytest
from sqlalchemy import text

from visit.domain.state.visit_status import ACTIVE_STATUSES, ALL_STATUSES, STARTED_STATUSES, STATUSES

pytestmark = pytest.mark.integration

_QUOTED = re.compile(r"'([a-z_]+)'")


def _ordered(codes: frozenset[str]) -> list[str]:
    return [s.code for s in STATUSES if s.code in codes]


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


async def test_상태_CHECK_는_표의_모든_상태를_표의_순서로_담는다(db_engine):
    assert _QUOTED.findall(await _constraint_def(db_engine, "ck_visits_status")) == _ordered(ALL_STATUSES)


async def test_시작_시각_CHECK_는_시작_시각이_있는_상태만_담는다(db_engine):
    assert _QUOTED.findall(await _constraint_def(db_engine, "ck_visits_started_at")) == _ordered(STARTED_STATUSES)


@pytest.mark.parametrize("index", ["uq_visits_pet_start_active", "uq_visits_customer_start_active"])
async def test_중복_예약_부분_색인은_살아_있는_상태만_담는다(db_engine, index):
    assert _QUOTED.findall(await _index_predicate(db_engine, index)) == _ordered(ACTIVE_STATUSES)
