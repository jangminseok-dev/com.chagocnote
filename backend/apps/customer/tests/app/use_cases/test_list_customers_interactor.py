from customer.app.dtos.customer_search_dto import SearchPage
from customer.app.dtos.list_customers_dto import ListCustomersQuery
from customer.app.use_cases.list_customers_interactor import ListCustomersInteractor
from customer.domain.entities.pet import PetCondition
from customer.domain.services.search_terms import SearchWord
from customer.tests.helpers.fakes import FakeLedger, FakeLibrary, FakeSearch, family, today
from customer.tests.helpers.profiles import ctx


def _query(**overrides):
    fields = dict(ctx=ctx(), q="5678 콩", sort="name", include_passed=False, cursor="abc")
    fields.update(overrides)
    return ListCustomersQuery(**fields)


def _setup():
    journal, customers, pets, _, _ = family()
    kim = customers.seed(name="김민지", phone="01012345678")
    park = customers.seed(name="박서준", phone="0212345678")
    pets.seed(kim.id, "콩이", conditions=[PetCondition("allergy", "알레르기", None, None)])
    pets.seed(kim.id, "별이", passed_away=True)
    pets.seed(park.id, "보리")
    search = FakeSearch(journal, SearchPage(customer_ids=[park.id, kim.id], next_cursor="next"), pet_count=2)
    return kim, park, search, ListCustomersInteractor(customers, pets, search, FakeLedger(journal), FakeLibrary(), today)


async def test_검색_순서대로_가족_카드를_만들고_번호는_가린다():
    kim, park, search, interactor = _setup()
    view = await interactor.list_customers(_query())
    assert [(c.customer_id, c.name, c.phone_masked) for c in view.items] == [
        (park.id, "박서준", "02-12··-5678"), (kim.id, "김민지", "010-12··-5678"),
    ]
    assert [(p.name, p.age_label, p.has_conditions) for p in view.items[1].pets] == [("콩이", "5살", True)]
    assert (view.next_cursor, view.pet_count) == ("next", 2)
    _, request = search.requests[0]
    assert request.words == (SearchWord("last4", "5678"), SearchWord("text", "콩"))
    assert (request.sort, request.include_passed, request.cursor, request.limit) == ("name", False, "abc", 30)


async def test_무지개다리를_포함하면_카드에도_보인다():
    kim, _, _, interactor = _setup()
    view = await interactor.list_customers(_query(include_passed=True))
    card = next(c for c in view.items if c.customer_id == kim.id)
    assert [(p.name, p.passed_away) for p in card.pets] == [("콩이", False), ("별이", True)]


async def test_검색_줄에_있어도_원본에_없는_가족은_빼고_원본을_따른다():
    journal, customers, pets, _, _ = family()
    kim = customers.seed()
    pets.seed(kim.id)
    search = FakeSearch(journal, SearchPage(customer_ids=[999, kim.id], next_cursor=None))
    view = await ListCustomersInteractor(customers, pets, search, FakeLedger(journal), FakeLibrary(),
                                         today).list_customers(_query())
    assert [c.customer_id for c in view.items] == [kim.id]


async def test_반려동물_줄마다_프로필_사진을_페이지_한_번에_묻는다():
    journal, customers, pets, _, _ = family()
    kim, park = customers.seed(), customers.seed(name="박서준", phone="0212345678")
    kong, bori = pets.seed(kim.id, "콩이"), pets.seed(park.id, "보리")
    ledger, library = FakeLedger(journal), FakeLibrary()
    ledger.covers, library.ready = {kong.id: 51}, {51}
    search = FakeSearch(journal, SearchPage(customer_ids=[kim.id, park.id], next_cursor=None))
    view = await ListCustomersInteractor(customers, pets, search, ledger, library, today).list_customers(_query())
    assert [(p.name, p.photo) for c in view.items for p in c.pets] == [("콩이", "t/51"), ("보리", None)]
    assert [e for e in journal if e[0] == "latest_covers"] == [("latest_covers", sorted([kong.id, bori.id]))]
