"""'최근 방문순' 복구 스크립트 — 어긋난 마지막 방문 시각을 원본(visits)대로 되돌린다."""
import pytest
from sqlalchemy import text

import scripts.rebuild_last_visit as rebuild_last_visit
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile
from scripts.rebuild_last_visit import rebuild_all
from visit.tests.helpers.builders import kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration


async def test_복구_스크립트의_엔진도_hide_parameters를_켠다(migrated_test_db, monkeypatch):
    captured = {}
    original_create = rebuild_last_visit.create_async_engine

    def _spy(url, **kwargs):
        captured.update(kwargs)
        return original_create(url, **kwargs)

    monkeypatch.setattr(rebuild_last_visit, "create_async_engine", _spy)
    monkeypatch.setattr(rebuild_last_visit, "DATABASE_URL", migrated_test_db)

    await rebuild_last_visit._run()

    assert captured.get("hide_parameters") is True


async def _customer(session, shop_id, phone):
    customer = await CustomerPgRepository(session).create(ctx(shop_id=shop_id), customer_profile(phone=phone))
    await PetPgRepository(session).add(ctx(shop_id=shop_id), customer.id, pet_profile())
    await CustomerSearchPgAdapter(session).rebuild_search_entry(ctx(shop_id=shop_id), customer.id)
    return customer.id


async def test_어긋난_마지막_방문_시각을_원본에서_다시_맞춘다(db_session):
    visited = await _customer(db_session, 1, "01012345678")
    never = await _customer(db_session, 2, "01099998888")
    await insert_visit(db_session, kst(9, 2, 14), "completed", customer_id=visited)
    await insert_visit(db_session, kst(9, 9, 14), "canceled", customer_id=visited)
    # 어긋난 상태: 방문한 고객은 비어 있고, 방문한 적 없는 고객에게 값이 있다.
    await db_session.execute(text("UPDATE customer_search_entries SET last_visit_at = now() WHERE customer_id = :id"),
                             {"id": never})
    await db_session.commit()

    assert await rebuild_all(db_session) == 2
    rows = dict((await db_session.execute(
        text("SELECT customer_id, last_visit_at FROM customer_search_entries"))).all())
    assert rows == {visited: kst(9, 2, 14), never: None}
