import pytest

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.domain.errors import CustomerHasUpcomingVisitsError, CustomerNotFoundError
from customer.tests.helpers.fakes import FakeLedger, family
from customer.tests.helpers.profiles import ctx


async def test_잠근_뒤_익명화하고_방문_메모와_검색_줄을_정리한다():
    journal, customers, _, _, search = family()
    customer = customers.seed()
    await DeleteCustomerInteractor(customers, search, FakeLedger(journal)).delete_customer(
        DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id)
    )
    assert journal == [("lock_customer", customer.id), ("anonymize", customer.id),
                       ("clear_visit_memos", customer.id), ("rebuild", customer.id)]


async def test_앞으로의_예약이_남았으면_CUSTOMER_HAS_UPCOMING_VISITS_다():
    """V7 — 익명화한 고객에게 앞으로의 예약이 남지 않게 한다. 고객 행을 잠근 뒤에 묻는다."""
    journal, customers, _, _, search = family()
    customer = customers.seed()
    ledger = FakeLedger(journal)
    ledger.customers_with_upcoming.add(customer.id)
    with pytest.raises(CustomerHasUpcomingVisitsError):
        await DeleteCustomerInteractor(customers, search, ledger).delete_customer(
            DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id)
        )
    assert journal == [("lock_customer", customer.id)]
    assert customer.id in customers.rows


async def test_이미_삭제했거나_다른_매장이면_404_다():
    journal, customers, _, _, search = family()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await DeleteCustomerInteractor(customers, search, FakeLedger(journal)).delete_customer(
            DeleteCustomerCommand(ctx=ctx(shop_id=1), customer_id=customer.id)
        )
    assert [entry[0] for entry in journal] == ["lock_customer"]
