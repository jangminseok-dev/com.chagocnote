import pytest

from customer.app.dtos.lookup_customer_dto import LookupCustomerQuery
from customer.app.use_cases.lookup_customer_interactor import LookupCustomerInteractor
from customer.domain.errors import CustomerInputError, CustomerNotFoundError
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx


async def test_하이픈을_넣은_번호로도_찾고_살아_있는_아이_이름만_준다():
    _, customers, pets, _, _ = family()
    customer = customers.seed(phone="01012345678")
    pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "두부")
    pets.seed(customer.id, "별이", passed_away=True)
    result = await LookupCustomerInteractor(customers, pets).lookup_customer(
        LookupCustomerQuery(ctx=ctx(), phone="010-1234-5678")
    )
    assert (result.customer_id, result.name, result.pet_names) == (customer.id, "김민지", ["콩이", "두부"])


async def test_없거나_다른_매장이면_CUSTOMER_NOT_FOUND_다():
    _, customers, pets, _, _ = family()
    customers.seed(shop_id=2, phone="01012345678")
    with pytest.raises(CustomerNotFoundError):
        await LookupCustomerInteractor(customers, pets).lookup_customer(
            LookupCustomerQuery(ctx=ctx(shop_id=1), phone="01012345678")
        )


async def test_번호_형식이_아니면_VALIDATION_ERROR_다():
    _, customers, pets, _, _ = family()
    with pytest.raises(CustomerInputError):
        await LookupCustomerInteractor(customers, pets).lookup_customer(
            LookupCustomerQuery(ctx=ctx(), phone="5678")
        )
