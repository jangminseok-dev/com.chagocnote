import pytest

from customer.app.dtos.get_customer_dto import GetCustomerQuery
from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
from customer.domain.errors import CustomerNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.profiles import ctx


async def test_보호자_전체와_반려동물_전체를_돌려준다():
    _, customers, pets, _, _ = family()
    customer = customers.seed()
    pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "별이", passed_away=True)
    view = await GetCustomerInteractor(customers, pets, today).get_customer(
        GetCustomerQuery(ctx=ctx(), customer_id=customer.id)
    )
    assert view.customer.phone == "01012345678"   # 상세는 전체 번호다
    assert [(p.name, p.passed_away_at is not None) for p in view.pets] == [("콩이", False), ("별이", True)]


async def test_다른_매장의_고객은_404_다():
    _, customers, pets, _, _ = family()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await GetCustomerInteractor(customers, pets, today).get_customer(
            GetCustomerQuery(ctx=ctx(shop_id=1), customer_id=customer.id)
        )
