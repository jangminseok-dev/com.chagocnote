from datetime import datetime, timezone

import pytest

from customer.app.dtos.get_customer_dto import GetCustomerQuery
from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
from customer.domain.errors import CustomerNotFoundError
from customer.tests.helpers.fakes import FakeLedger, FakeLibrary, family, today
from customer.tests.helpers.profiles import ctx
from hub.app.dtos.upcoming_visit import UpcomingVisit


async def test_보호자_전체와_반려동물_전체를_돌려준다():
    journal, customers, pets, _, _ = family()
    customer = customers.seed()
    pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "별이", passed_away=True)
    view = await GetCustomerInteractor(customers, pets, FakeLedger(journal), FakeLibrary(), today).get_customer(
        GetCustomerQuery(ctx=ctx(), customer_id=customer.id)
    )
    assert view.customer.phone == "01012345678"   # 상세는 전체 번호다
    assert [(p.name, p.passed_away_at is not None) for p in view.pets] == [("콩이", False), ("별이", True)]
    assert (view.no_show_count, view.upcoming_visits, view.photos) == (0, [], {})


async def test_노쇼_횟수와_다가오는_예약을_아이_이름과_함께_매장_시간대로():
    journal, customers, pets, _, _ = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    ledger = FakeLedger(journal)
    ledger.no_shows[customer.id] = 2
    ledger.upcoming[customer.id] = [
        UpcomingVisit(visit_id=7, pet_id=kong.id, starts_at=datetime(2026, 10, 2, 5, tzinfo=timezone.utc)),
        UpcomingVisit(visit_id=8, pet_id=None, starts_at=datetime(2026, 10, 3, 5, tzinfo=timezone.utc)),
    ]
    view = await GetCustomerInteractor(customers, pets, ledger, FakeLibrary(), today).get_customer(
        GetCustomerQuery(ctx=ctx(), customer_id=customer.id)
    )
    assert view.no_show_count == 2
    assert [(u.visit_id, u.pet_name, u.starts_at.isoformat()) for u in view.upcoming_visits] == [
        (7, "콩이", "2026-10-02T14:00:00+09:00"), (8, None, "2026-10-03T14:00:00+09:00")]


async def test_다른_매장의_고객은_404_다():
    journal, customers, pets, _, _ = family()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await GetCustomerInteractor(customers, pets, FakeLedger(journal), FakeLibrary(), today).get_customer(
            GetCustomerQuery(ctx=ctx(shop_id=1), customer_id=customer.id)
        )


async def test_반려동물마다_프로필_사진을_한_번에_묻는다():
    journal, customers, pets, _, _ = family()
    customer = customers.seed()
    kong, byeol = pets.seed(customer.id, "콩이"), pets.seed(customer.id, "별이")
    ledger, library = FakeLedger(journal), FakeLibrary()
    ledger.covers = {kong.id: 51, byeol.id: 52}
    library.ready = {51}   # 52 는 URL 을 줄 수 없다(정리됐다) — 빠진다
    view = await GetCustomerInteractor(customers, pets, ledger, library, today).get_customer(
        GetCustomerQuery(ctx=ctx(), customer_id=customer.id))
    assert view.photos == {kong.id: "t/51"}
    assert journal.count(("latest_covers", sorted([kong.id, byeol.id]))) == 1
