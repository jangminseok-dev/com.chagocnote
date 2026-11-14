import pytest

from customer.app.dtos.update_customer_dto import UpdateCustomerCommand
from customer.app.use_cases.update_customer_interactor import UpdateCustomerInteractor
from customer.domain.errors import CustomerInputError, CustomerNotFoundError
from customer.tests.helpers.fakes import FakeEvents, family, today
from customer.tests.helpers.inputs import customer_input
from customer.tests.helpers.profiles import ctx


def _setup(consent=False):
    journal, customers, pets, _, search = family()
    customer = customers.seed(consent=consent)
    pets.seed(customer.id)
    return journal, customer, UpdateCustomerInteractor(customers, pets, search, today, events=FakeEvents())


async def test_잠근_뒤_고치고_검색_줄을_다시_만든다():
    journal, customer, interactor = _setup()
    view = await interactor.update_customer(UpdateCustomerCommand(
        ctx=ctx(), customer_id=customer.id, customer=customer_input(name="김민지(콩이 엄마)"),
    ))
    assert view.customer.name == "김민지(콩이 엄마)"
    assert journal == [("lock_customer", customer.id), ("update_customer", customer.id, False),
                       ("rebuild", customer.id)]


async def test_동의가_바뀔_때만_동의_시각을_바꾸라고_한다():
    journal, customer, interactor = _setup(consent=False)
    await interactor.update_customer(UpdateCustomerCommand(
        ctx=ctx(), customer_id=customer.id, customer=customer_input(marketing_consent=True),
    ))
    assert ("update_customer", customer.id, True) in journal


async def test_다른_매장이면_404_이고_아무것도_쓰지_않는다():
    journal, customer, interactor = _setup()
    with pytest.raises(CustomerNotFoundError):
        await interactor.update_customer(UpdateCustomerCommand(
            ctx=ctx(shop_id=2), customer_id=customer.id, customer=customer_input(),
        ))
    assert [entry[0] for entry in journal] == ["lock_customer"]


async def test_번호_형식이_틀리면_잠그기_전에_막는다():
    journal, customer, interactor = _setup()
    with pytest.raises(CustomerInputError):
        await interactor.update_customer(UpdateCustomerCommand(
            ctx=ctx(), customer_id=customer.id, customer=customer_input(phone="12"),
        ))
    assert journal == []


async def test_고치면_보호자를_다시_색인하라고_알린다():
    _, customers, pets, _, search = family()
    customer = customers.seed()
    events = FakeEvents()
    await UpdateCustomerInteractor(customers, pets, search, today, events=events).update_customer(
        UpdateCustomerCommand(ctx=ctx(), customer_id=customer.id, customer=customer_input(memo="현관 비밀번호 문의")))
    assert events.changed == [("customer", customer.id)]
