import pytest

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.domain.errors import CustomerNotFoundError
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx


async def test_잠근_뒤_익명화하고_검색_줄을_정리한다():
    journal, customers, _, _, search = family()
    customer = customers.seed()
    await DeleteCustomerInteractor(customers, search).delete_customer(
        DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id)
    )
    assert journal == [("lock_customer", customer.id), ("anonymize", customer.id), ("rebuild", customer.id)]


async def test_이미_삭제했거나_다른_매장이면_404_다():
    journal, customers, _, _, search = family()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await DeleteCustomerInteractor(customers, search).delete_customer(
            DeleteCustomerCommand(ctx=ctx(shop_id=1), customer_id=customer.id)
        )
    assert [entry[0] for entry in journal] == ["lock_customer"]
