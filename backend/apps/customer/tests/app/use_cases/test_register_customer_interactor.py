import pytest

from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.use_cases.register_customer_interactor import RegisterCustomerInteractor
from customer.domain.errors import CustomerInputError, CustomerPhoneTakenError, PetHealthRequiredError
from customer.tests.helpers.fakes import FakeEvents, family, today
from customer.tests.helpers.inputs import customer_input, pet_input
from customer.tests.helpers.profiles import condition, ctx


def _interactor():
    journal, customers, pets, types, search = family()
    return journal, customers, RegisterCustomerInteractor(customers, pets, types, search, today, events=FakeEvents())


async def test_보호자와_첫_반려동물을_넣고_검색_줄을_만든_뒤_상세를_돌려준다():
    journal, _, interactor = _interactor()
    view = await interactor.register_customer(RegisterCustomerCommand(
        ctx=ctx(), customer=customer_input(),
        pet=pet_input(no_known_conditions=False, conditions=(condition("allergy", note="닭고기"),)),
    ))
    assert view.customer.phone == "01012345678"   # 숫자만 저장한다
    assert [(p.name, p.age_label, p.has_conditions) for p in view.pets] == [("콩이", "5살", True)]
    assert journal == [("create_customer", 1), ("add_pet", 1), ("rebuild", 1)]


async def test_반려동물_폼이_틀리면_아무것도_쓰지_않는다():
    journal, customers, interactor = _interactor()
    with pytest.raises(PetHealthRequiredError):
        await interactor.register_customer(RegisterCustomerCommand(
            ctx=ctx(), customer=customer_input(), pet=pet_input(no_known_conditions=False),
        ))
    with pytest.raises(CustomerInputError):
        await interactor.register_customer(RegisterCustomerCommand(
            ctx=ctx(), customer=customer_input(phone="12"), pet=pet_input(),
        ))
    assert journal == [] and customers.rows == {}


async def test_번호가_겹치면_CUSTOMER_PHONE_TAKEN_이다():
    journal, customers, interactor = _interactor()
    customers.seed(phone="01012345678")
    with pytest.raises(CustomerPhoneTakenError):
        await interactor.register_customer(RegisterCustomerCommand(
            ctx=ctx(), customer=customer_input(), pet=pet_input(),
        ))
    assert journal == []


async def test_등록하면_보호자와_첫_아이를_다시_색인하라고_알린다():
    _, customers, pets, types, search = family()
    events = FakeEvents()
    view = await RegisterCustomerInteractor(customers, pets, types, search, today, events=events).register_customer(
        RegisterCustomerCommand(ctx=ctx(), customer=customer_input(), pet=pet_input()))
    assert events.changed == [("customer", view.customer.customer_id), ("pet", view.pets[0].pet_id)]


async def test_등록이_거절되면_알리지_않는다():
    _, customers, pets, types, search = family()
    events = FakeEvents()
    with pytest.raises(PetHealthRequiredError):
        await RegisterCustomerInteractor(customers, pets, types, search, today, events=events).register_customer(
            RegisterCustomerCommand(ctx=ctx(), customer=customer_input(),
                                    pet=pet_input(no_known_conditions=False, conditions=())))
    assert events.changed == []
