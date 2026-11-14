from hub.app.ports.search_index_port import SearchIndexPort
from search.app.use_cases.forget_customer_interactor import ForgetCustomerInteractor
from search.domain.entities.search_document import KINDS
from search.tests.helpers.builders import NOW, ctx, doc
from search.tests.helpers.fakes import FakeDocuments, FakeQueue


def _use_case():
    documents, queue = FakeDocuments(), FakeQueue()
    return documents, queue, ForgetCustomerInteractor(documents=documents, queue=queue, now=lambda: NOW)


async def test_그_고객의_문서를_종류와_상관없이_전부_지운다():
    documents, _, use_case = _use_case()
    documents.seed(1, *(doc(kind, 10 + i, customer_id=1) for i, kind in enumerate(KINDS)))
    documents.seed(1, doc("care_note", 99, customer_id=2, body="다른 보호자의 글"))
    await use_case.forget_customer(ctx(), 1)
    assert [d.customer_id for d in documents.of_shop(1)] == [2]


async def test_다른_매장의_같은_번호_고객은_건드리지_않는다():
    documents, _, use_case = _use_case()
    documents.seed(1, doc("pet_memo", 101, customer_id=1))
    documents.seed(2, doc("pet_memo", 101, customer_id=1))
    await use_case.forget_customer(ctx(1), 1)
    assert documents.of_shop(1) == [] and len(documents.of_shop(2)) == 1


async def test_뒤에서_한_번_더_맞추도록_줄을_넣는다():
    _, queue, use_case = _use_case()
    await use_case.forget_customer(ctx(), 1)
    assert queue.targets() == [(1, "customer", 1)]


def test_허브_포트의_구현이다():
    assert isinstance(_use_case()[2], SearchIndexPort)
