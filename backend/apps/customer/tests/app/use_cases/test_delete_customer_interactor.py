import pytest

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.domain.errors import CustomerHasUpcomingVisitsError, CustomerNotFoundError
from customer.tests.helpers.fakes import FakeLedger, FakeSearchIndex, consent_stores, family
from customer.tests.helpers.profiles import ctx


class _Guardians:
    """GuardianLifecyclePort 스텁 — 부른 것을 journal 에 남긴다."""

    def __init__(self, journal):
        self.journal = journal

    async def end_for_customer(self, shop_id, customer_id):
        self.journal.append(("end_guardian_links", shop_id, customer_id))
        return 1


async def test_잠근_뒤_익명화하고_방문_메모와_검색_줄을_정리한다():
    journal, customers, _, _, search = family()
    customer = customers.seed()
    await DeleteCustomerInteractor(
        customers, search, FakeLedger(journal), _Guardians(journal), index=FakeSearchIndex(journal), **consent_stores(journal),
    ).delete_customer(DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id))
    # 익명화한 뒤 서류를 지우고 보호자 연결을 끝낸다 — 고객 행을 잠근 채다(잠금 순서: 고객 행 → 서류 요청 행 → 보호자 연결 행).
    assert journal == [("lock_customer", customer.id), ("anonymize", customer.id),
                       ("lock_forms", customer.id), ("delete_signatures_of_customer", customer.id),
                       ("end_guardian_links", 1, customer.id),
                       ("clear_visit_memos", customer.id), ("forget_search", customer.id),
                       ("rebuild", customer.id)]


async def test_앞으로의_예약이_남았으면_CUSTOMER_HAS_UPCOMING_VISITS_다():
    """V7 — 익명화한 고객에게 앞으로의 예약이 남지 않게 한다. 고객 행을 잠근 뒤에 묻는다."""
    journal, customers, _, _, search = family()
    customer = customers.seed()
    ledger = FakeLedger(journal)
    ledger.customers_with_upcoming.add(customer.id)
    with pytest.raises(CustomerHasUpcomingVisitsError):
        await DeleteCustomerInteractor(customers, search, ledger, _Guardians(journal), index=FakeSearchIndex(journal), **consent_stores(journal)).delete_customer(
            DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id)
        )
    assert journal == [("lock_customer", customer.id)]
    assert customer.id in customers.rows


async def test_이미_삭제했거나_다른_매장이면_404_다():
    journal, customers, _, _, search = family()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await DeleteCustomerInteractor(customers, search, FakeLedger(journal), _Guardians(journal), index=FakeSearchIndex(journal), **consent_stores(journal)).delete_customer(
            DeleteCustomerCommand(ctx=ctx(shop_id=1), customer_id=customer.id)
        )
    assert [entry[0] for entry in journal] == ["lock_customer"]


async def test_예약이_남아_익명화하지_못하면_검색_문서도_지우지_않는다():
    journal, customers, _, _, search = family()
    customer = customers.seed()
    ledger = FakeLedger(journal)
    ledger.customers_with_upcoming.add(customer.id)
    with pytest.raises(CustomerHasUpcomingVisitsError):
        await DeleteCustomerInteractor(
            customers, search, ledger, _Guardians(journal), index=FakeSearchIndex(journal), **consent_stores(journal),
        ).delete_customer(DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id))
    assert ("forget_search", customer.id) not in journal
