"""알림장(0010)의 부분 유일 색인과 CHECK 가 실제 DB 에 있는지 — 실제 DB 에서 읽고 넣어 본다.

tests/test_schema_drift.py 의 compare_metadata 는 CHECK 와 부분 색인의 WHERE 를 비교하지 않는다. ORM 에만 적고
마이그레이션에서 빠뜨리면 여기서 걸린다.
"""
from datetime import timedelta

import pytest
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import IntegrityError

from visit.adapter.outbound.orm.visit_orm import VisitReportOrm, VisitShopSettingsOrm
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A = ctx(shop_id=1)
NOW = kst(9, 28, 15)


async def test_끊지_않은_줄의_부분_유일_색인이다(db_engine):
    async with db_engine.connect() as conn:
        unique, columns, predicate = (await conn.execute(text(
            "SELECT i.indisunique, pg_get_indexdef(i.indexrelid, 1, true), pg_get_expr(i.indpred, i.indrelid) "
            "FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid WHERE c.relname = 'uq_visit_reports_live'"
        ))).one()
    assert (unique, columns, predicate) == (True, "visit_id", "(revoked_at IS NULL)")


def _report(visit_id, **overrides):
    return insert(VisitReportOrm).values(**{
        "visit_id": visit_id, "public_id": b"\x01" * 16, "expires_at": None, "created_by_member_id": 11,
        "created_at": NOW, **overrides})


@pytest.mark.parametrize("expires_at", [NOW, NOW - timedelta(seconds=1)])
async def test_기간은_보낸_시각보다_뒤여야_한다(db_session, expires_at):
    visit_id = await insert_visit(db_session, kst(9, 28, 14), "completed")
    with pytest.raises(IntegrityError, match="ck_visit_reports_expires"):
        await db_session.execute(_report(visit_id, expires_at=expires_at))


@pytest.mark.parametrize("public_id", [b"", b"\x01" * 15, b"\x01" * 17])
async def test_public_id_는_16바이트여야_한다(db_session, public_id):
    visit_id = await insert_visit(db_session, kst(9, 28, 14), "completed")
    with pytest.raises(IntegrityError, match="ck_visit_reports_public_id"):
        await db_session.execute(_report(visit_id, public_id=public_id))


async def test_public_id_는_방문이_달라도_겹칠_수_없다(db_session):
    first = await insert_visit(db_session, kst(9, 28, 14), "completed")
    second = await insert_visit(db_session, kst(9, 29, 14), "completed")
    await db_session.execute(_report(first))
    with pytest.raises(IntegrityError, match="visit_reports_public_id_key"):
        await db_session.execute(_report(second))


async def test_새_칸의_기본값은_기간_30일_메뉴와_매장_정보만_보이기다(db_session):
    await SchedulePgRepository(db_session).ensure(A)
    row = (await db_session.execute(select(
        VisitShopSettingsOrm.report_link_days, VisitShopSettingsOrm.report_show_menus,
        VisitShopSettingsOrm.report_show_shop_info, VisitShopSettingsOrm.report_show_weight,
        VisitShopSettingsOrm.report_show_amount,
    ))).one()
    assert tuple(row) == (30, True, True, False, False)


def _set_link_days(days):
    return update(VisitShopSettingsOrm).where(VisitShopSettingsOrm.shop_id == 1).values(report_link_days=days)


@pytest.mark.parametrize("days", [1, 0, -1, 31, 8, 29])
async def test_링크_기간은_7일과_30일만_받는다(db_session, days):
    await SchedulePgRepository(db_session).ensure(A)
    with pytest.raises(IntegrityError, match="ck_visit_shop_settings_report_link_days"):
        await db_session.execute(_set_link_days(days))


@pytest.mark.parametrize("days", [7, 30, None])
async def test_링크_기간_7일_30일_무기한은_받는다(db_session, days):
    await SchedulePgRepository(db_session).ensure(A)
    await db_session.execute(_set_link_days(days))
    assert (await db_session.execute(select(VisitShopSettingsOrm.report_link_days))).scalar_one() == days
