from dataclasses import replace
from datetime import date

import pytest

from customer.app.dtos.clear_customer_caution_dto import ClearCustomerCautionCommand
from customer.app.dtos.customer_search_dto import SearchPage
from customer.app.dtos.list_customers_dto import ListCustomersQuery
from customer.app.dtos.set_customer_caution_dto import SetCustomerCautionCommand
from customer.app.services.detail_reader import read_customer_detail, read_pet_detail
from customer.app.use_cases.clear_customer_caution_interactor import ClearCustomerCautionInteractor
from customer.app.use_cases.list_customers_interactor import ListCustomersInteractor
from customer.app.use_cases.set_customer_caution_interactor import SetCustomerCautionInteractor
from customer.domain.errors import CustomerInputError, CustomerNotFoundError
from customer.tests.helpers.fakes import TODAY, FakeLedger, FakeLibrary, FakeSearch, family, today
from customer.tests.helpers.profiles import ctx

UNTIL = date(2027, 9, 22)   # TODAY(2026-09-22) + 365일


def _set(customers, pets):
    return SetCustomerCautionInteractor(customers, pets, today)


async def test_사유를_다듬어_달고_끝나는_날은_365일_뒤다():
    journal, customers, pets, _, _ = family()
    customer = customers.seed()
    pets.seed(customer.id)

    view = await _set(customers, pets).set_customer_caution(
        SetCustomerCautionCommand(ctx=ctx(member_id=42), customer_id=customer.id, reason="  노쇼 2번 \n")
    )

    assert (view.customer.caution.reason, view.customer.caution.until) == ("노쇼 2번", UNTIL)
    assert journal == [("lock_customer", customer.id), ("set_caution", customer.id, "노쇼 2번", UNTIL, 42)]


async def test_다시_달면_사유와_끝나는_날이_새로_정해진다():
    _, customers, pets, _, _ = family()
    customer = customers.seed()
    customers.rows[customer.id] = replace(customer, caution_reason="옛 사유", caution_until=date(2026, 10, 1))

    view = await _set(customers, pets).set_customer_caution(
        SetCustomerCautionCommand(ctx=ctx(), customer_id=customer.id, reason="입질")
    )

    assert (view.customer.caution.reason, view.customer.caution.until) == ("입질", UNTIL)


@pytest.mark.parametrize("reason", ["", "   ", "가" * 101])
async def test_사유가_비었거나_길면_잠그기_전에_거절한다(reason):
    journal, customers, pets, _, _ = family()
    customer = customers.seed()
    with pytest.raises(CustomerInputError):
        await _set(customers, pets).set_customer_caution(
            SetCustomerCautionCommand(ctx=ctx(), customer_id=customer.id, reason=reason)
        )
    assert journal == []
    assert customers.rows[customer.id].caution_reason is None


async def test_다른_매장의_고객에게는_달지_못한다():
    _, customers, pets, _, _ = family()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await _set(customers, pets).set_customer_caution(
            SetCustomerCautionCommand(ctx=ctx(shop_id=1), customer_id=customer.id, reason="노쇼")
        )
    assert customers.rows[customer.id].caution_reason is None


async def test_직원도_달고_푼다():
    _, customers, pets, _, _ = family()
    customer = customers.seed()
    staff = ctx(role="staff")
    await _set(customers, pets).set_customer_caution(
        SetCustomerCautionCommand(ctx=staff, customer_id=customer.id, reason="노쇼")
    )
    view = await ClearCustomerCautionInteractor(customers, pets, today).clear_customer_caution(
        ClearCustomerCautionCommand(ctx=staff, customer_id=customer.id)
    )
    assert view.customer.caution is None


async def test_풀면_칸이_비고_없던_것을_풀어도_된다():
    journal, customers, pets, _, _ = family()
    customer = customers.seed()
    clear = ClearCustomerCautionInteractor(customers, pets, today)

    view = await clear.clear_customer_caution(ClearCustomerCautionCommand(ctx=ctx(), customer_id=customer.id))

    assert view.customer.caution is None
    assert journal == [("lock_customer", customer.id), ("set_caution", customer.id, None, None, None)]


@pytest.mark.parametrize("until,shown", [
    (date(2026, 9, 22), True),    # 끝나는 날 당일
    (date(2026, 9, 21), False),   # 하루 지남
])
async def test_기한이_지난_주의는_상세와_목록_어디에도_없다(until, shown):
    journal, customers, pets, _, _ = family()
    customer = customers.seed()
    pet = pets.seed(customer.id)
    customers.rows[customer.id] = replace(customer, caution_reason="노쇼", caution_until=until)

    detail = await read_customer_detail(ctx(), customer.id, customers, pets, TODAY)
    pet_detail = await read_pet_detail(ctx(), pet.id, customers, pets, TODAY)
    listed = await ListCustomersInteractor(
        customers, pets, FakeSearch(journal, SearchPage(customer_ids=[customer.id], next_cursor=None)),
        FakeLedger(journal), FakeLibrary(), today,
    ).list_customers(ListCustomersQuery(ctx=ctx(), q=None, sort="recent", include_passed=False, cursor=None))

    assert (detail.customer.caution is not None) is shown
    assert (pet_detail.caution is not None) is shown
    assert listed.items[0].caution is shown
    if shown:
        assert (pet_detail.caution.reason, pet_detail.caution.until) == ("노쇼", until)


async def test_주의가_없는_고객은_칸이_비어_있다():
    _, customers, pets, _, _ = family()
    customer = customers.seed()
    pet = pets.seed(customer.id)
    assert (await read_customer_detail(ctx(), customer.id, customers, pets, TODAY)).customer.caution is None
    assert (await read_pet_detail(ctx(), pet.id, customers, pets, TODAY)).caution is None
