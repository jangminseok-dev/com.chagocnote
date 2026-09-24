"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.tests.helpers.fakes import (
    FakeConditionTypes,
    FakeCustomers,
    FakeLedger,
    FakePets,
    FakeSearch,
    Journal,
)
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    journal = Journal()
    customers = FakeCustomers(journal)
    assert isinstance(FakeConditionTypes(), ConditionTypeRepository)
    assert isinstance(customers, CustomerRepository)
    assert isinstance(FakePets(journal, customers), PetRepository)
    assert isinstance(FakeSearch(journal), CustomerSearchPort)
    assert isinstance(FakeLedger(journal), VisitLedgerPort)
