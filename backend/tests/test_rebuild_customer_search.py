"""검색 줄 재생성 스크립트 — 어긋난 줄을 원본대로 되돌리고, 익명화한 고객의 줄은 지운다."""
import pytest
from sqlalchemy import text

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile
from scripts.rebuild_customer_search import rebuild_all

pytestmark = pytest.mark.integration


async def test_어긋난_검색_줄을_원본에서_다시_만든다(db_session):
    customers, pets = CustomerPgRepository(db_session), PetPgRepository(db_session)
    alive = await customers.create(ctx(shop_id=1), customer_profile())
    await pets.add(ctx(shop_id=1), alive.id, pet_profile())
    gone = await customers.create(ctx(shop_id=2), customer_profile(phone="01099998888"))
    await customers.anonymize(ctx(shop_id=2), gone.id)
    # 어긋난 상태: 살아 있는 고객의 줄은 없고, 익명화한 고객의 줄이 남아 있다.
    await db_session.execute(text(
        "INSERT INTO customer_search_entries (customer_id, shop_id, terms, phone_last4, sort_name, "
        "last_activity_at) VALUES (:id, 2, '옛 이름', '8888', '옛 이름', now())"
    ), {"id": gone.id})

    assert await rebuild_all(db_session) == 2
    rows = (await db_session.execute(text(
        "SELECT customer_id, shop_id, terms FROM customer_search_entries"
    ))).all()
    assert [tuple(r) for r in rows] == [(alive.id, 1, "김민지 ㄱㅁㅈ 콩이 ㅋㅇ 01012345678")]
    assert await rebuild_all(db_session) == 2   # 다시 돌려도 같다
