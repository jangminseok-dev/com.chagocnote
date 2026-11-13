"""guardian_links 의 실제 CHECK·부분 색인이 도메인 튜플과 같은 값을 같은 순서로 말하는지 — 실제 DB 에서 읽는다."""
import re

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from guardian.domain.entities.guardian_link import ENDED_BY, VERIFIED_BY

pytestmark = pytest.mark.integration

_QUOTED = re.compile(r"'([a-z_]+)'")


async def _constraint_def(engine, name: str) -> str:
    async with engine.connect() as conn:
        return (await conn.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"), {"name": name}
        )).scalar_one()


@pytest.mark.parametrize(("name", "values"), [
    ("ck_guardian_links_verified_by", VERIFIED_BY),
    ("ck_guardian_links_ended_by", ENDED_BY),
])
async def test_CHECK_는_도메인_튜플의_값을_같은_순서로_담는다(db_engine, name, values):
    assert _QUOTED.findall(await _constraint_def(db_engine, name)) == list(values)


async def test_살아_있는_연결의_부분_유일_색인은_끝나지_않은_줄만_본다(db_engine):
    async with db_engine.connect() as conn:
        predicate = (await conn.execute(text(
            "SELECT pg_get_expr(i.indpred, i.indrelid) FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
            "WHERE c.relname = 'uq_guardian_links_live'"))).scalar_one()
    assert "ended_at IS NULL" in predicate


async def test_끝난_시각과_끝낸_쪽은_함께_있거나_함께_없다(db_engine):
    base = ("INSERT INTO guardian_links (user_id, shop_id, customer_id, verified_by, created_at, ended_at, ended_by) "
            "VALUES (1, 1, 1, 'report_link', now(), {at}, {by})")
    for at, by in (("NULL", "'shop'"), ("now()", "NULL")):
        with pytest.raises(IntegrityError):
            async with db_engine.begin() as conn:
                await conn.execute(text(base.format(at=at, by=by)))
