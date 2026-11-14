"""색인기 — 줄을 집어 원본을 읽고, 벡터를 받아, 고객 행을 잠근 뒤 다시 읽어 같을 때만 갈아 끼운다."""
import logging
from datetime import timedelta

import pytest

from hub.app.dtos.search_source import SourceDocument
from hub.app.errors import FamilyNotFoundError
from search.app.ports.output.embedding_port import INDEX_TIMEOUT
from search.app.services.indexer import Indexer, IndexReport
from search.domain.services.embedding_model import CURRENT_MODEL
from search.tests.helpers.builders import NOW, ctx, doc
from search.tests.helpers.fakes import FakeDocuments, FakeEmbedder, FakeQueue, FakeShops, FakeSource

SECRET = "귀를 만지면 무는 아이라 입마개가 필요해요"


def src(kind="care_note", source_id=7, body="얌전했어요", customer_id=1, pet_id=101) -> SourceDocument:
    d = doc(kind, source_id, customer_id=customer_id, pet_id=pet_id, body=body)
    return SourceDocument(kind=d.kind, source_id=d.source_id, customer_id=d.customer_id, pet_id=d.pet_id,
                          visit_id=d.visit_id, happened_on=d.happened_on, body=d.body)


class _Directory:
    """CustomerDirectoryPort 의 lock_family 만 — gone 의 고객은 익명화한 것으로 본다."""

    def __init__(self, journal):
        self.journal = journal
        self.gone: set[int] = set()

    async def lock_family(self, ctx, customer_id, pet_ids):
        self.journal.append(("lock_family", ctx.shop_id, customer_id, pet_ids))
        if customer_id in self.gone:
            raise FamilyNotFoundError("고객을 찾을 수 없습니다.")


class _World:
    def __init__(self, batch=20):
        self.journal: list = []
        self.queue, self.documents = FakeQueue(), FakeDocuments(self.journal)
        self.embedder, self.source = FakeEmbedder(self.journal), FakeSource(self.journal)
        self.directory, self.shops = _Directory(self.journal), FakeShops()
        self.now = NOW
        self.indexer = Indexer(
            queue=self.queue, documents=self.documents, embedder=self.embedder,
            sources={"visit": self.source, "pet": self.source, "customer": self.source},
            shops=self.shops, directory=self.directory, commit=self._commit, rollback=self._rollback,
            now=lambda: self.now, batch=batch,
        )

    async def _commit(self):
        self.journal.append(("commit",))

    async def _rollback(self):
        self.journal.append(("rollback",))

    async def changed(self, scope="visit", ref_id=7, shop_id=1):
        await self.queue.enqueue(ctx(shop_id), scope, ref_id, self.now)

    async def run(self, later=timedelta(0)) -> IndexReport:
        self.now += later
        return await self.indexer.run_once()

    def stored(self, shop_id=1):
        return {(d.kind, d.source_id): d for d in self.documents.of_shop(shop_id)}


async def test_줄을_집어_문서를_벡터와_함께_넣고_줄을_지운다():
    world = _World()
    world.source.put(1, "visit", 7, src("care_note", 7, "얌전했어요"), src("visit_memo", 7, "발톱 짧게"))
    await world.changed()
    assert await world.run() == IndexReport(claimed=1, indexed=1, deferred=0)
    stored = world.stored()
    assert stored[("care_note", 7)].embedding == FakeEmbedder.vector_of("얌전했어요")
    assert stored[("visit_memo", 7)].embedding == FakeEmbedder.vector_of("발톱 짧게")
    assert {d.model for d in stored.values()} == {CURRENT_MODEL}
    assert world.embedder.calls == [("passage", ["얌전했어요", "발톱 짧게"])]
    assert world.queue.jobs == {}


async def test_줄이_없으면_아무것도_하지_않는다():
    world = _World()
    assert await world.run() == IndexReport(claimed=0, indexed=0, deferred=0)
    assert world.embedder.calls == [] and world.documents.writes == []


async def test_원본이_비면_문서를_지우고_줄을_지운다():
    """글을 비웠거나, 기록·반려동물을 지웠거나, 익명화했다."""
    world = _World()
    world.documents.seed(1, doc("care_note", 7), doc("visit_memo", 7), doc("care_note", 8))
    await world.changed()
    assert await world.run() == IndexReport(claimed=1, indexed=1, deferred=0)
    assert list(world.stored()) == [("care_note", 8)]
    assert world.embedder.calls == [] and world.queue.jobs == {}


async def test_임베딩이_죽어_있으면_글만_넣고_줄을_남겨_미룬다():
    world = _World()
    world.source.put(1, "visit", 7, src())
    world.embedder.down = True
    await world.changed()
    assert await world.run() == IndexReport(claimed=1, indexed=0, deferred=1)
    [stored] = world.documents.of_shop(1)
    assert (stored.body, stored.embedding, stored.model) == ("얌전했어요", None, None)   # 글자로는 찾아진다
    [job] = world.queue.jobs.values()
    assert job.attempts == 1 and world.queue.due[job.id] == NOW + timedelta(seconds=30)


async def test_임베딩이_살아나면_다음_번에_벡터가_채워지고_줄이_사라진다():
    world = _World()
    world.source.put(1, "visit", 7, src())
    world.embedder.down = True
    await world.changed()
    await world.run()
    world.embedder.down = False
    assert (await world.run(later=timedelta(seconds=29))).claimed == 0          # 아직 때가 아니다
    assert await world.run(later=timedelta(seconds=1)) == IndexReport(claimed=1, indexed=1, deferred=0)
    [stored] = world.documents.of_shop(1)
    assert stored.embedding == FakeEmbedder.vector_of("얌전했어요") and stored.model == CURRENT_MODEL
    assert world.queue.jobs == {}


async def test_글이_그대로이고_벡터가_지금_모델의_것이면_다시_임베딩하지_않는다():
    world = _World()
    kept = FakeEmbedder.vector_of("옛 벡터")
    world.documents.seed(1, doc("care_note", 7, body="얌전했어요", embedding=kept, model=CURRENT_MODEL),
                         doc("visit_memo", 7, body="발톱 짧게", embedding=kept, model=CURRENT_MODEL))
    world.source.put(1, "visit", 7, src("care_note", 7, "얌전했어요"), src("visit_memo", 7, "발톱은 길게"))
    await world.changed()
    await world.run()
    assert world.embedder.calls == [("passage", ["발톱은 길게"])]           # 바뀐 글만 보낸다
    stored = world.stored()
    assert stored[("care_note", 7)].embedding == kept
    assert stored[("visit_memo", 7)].embedding == FakeEmbedder.vector_of("발톱은 길게")


async def test_바뀐_글이_없으면_임베딩을_부르지_않고_줄을_지운다():
    world = _World()
    world.documents.seed(1, doc("care_note", 7, embedding=FakeEmbedder.vector_of("x"), model=CURRENT_MODEL))
    world.source.put(1, "visit", 7, src())
    world.embedder.down = True
    await world.changed()
    assert await world.run() == IndexReport(claimed=1, indexed=1, deferred=0)
    assert world.embedder.calls == [] and world.queue.jobs == {}


async def test_다른_모델의_벡터와_벡터_없는_문서는_다시_임베딩한다():
    world = _World()
    world.documents.seed(1, doc("care_note", 7, embedding=FakeEmbedder.vector_of("x"), model="old-model"),
                         doc("visit_memo", 7, body="발톱 짧게"))
    world.source.put(1, "visit", 7, src("care_note", 7, "얌전했어요"), src("visit_memo", 7, "발톱 짧게"))
    await world.changed()
    await world.run()
    assert world.embedder.calls == [("passage", ["얌전했어요", "발톱 짧게"])]
    assert {d.model for d in world.documents.of_shop(1)} == {CURRENT_MODEL}


async def test_임베딩하는_사이에_원본이_바뀌면_쓰지_않고_줄을_남긴다():
    """옛 글을 되살리지 않는다 — 고객 행을 잠근 뒤 다시 읽어 견준다."""
    world = _World()
    world.source.put(1, "visit", 7, src(body="옛 글"))
    await world.changed()

    async def edit():
        world.source.put(1, "visit", 7, src(body="새 글"))

    world.embedder.during = edit
    assert await world.run() == IndexReport(claimed=1, indexed=0, deferred=1)
    assert world.documents.writes == [] and world.documents.of_shop(1) == []
    assert len(world.queue.jobs) == 1
    assert world.journal[-1] == ("rollback",)                 # 고객 행 잠금을 놓는다

    world.embedder.during = None
    await world.run(later=timedelta(seconds=60))               # 집은 줄은 60초 뒤에 다시 집힌다
    assert [d.body for d in world.documents.of_shop(1)] == ["새 글"] and world.queue.jobs == {}


async def test_임베딩하는_사이에_익명화되면_문서를_지우고_끝낸다():
    world = _World()
    world.documents.seed(1, doc("care_note", 7, body="옛 글"))
    world.source.put(1, "visit", 7, src(body="새 글"))
    await world.changed()

    async def anonymize():
        world.directory.gone.add(1)

    world.embedder.during = anonymize
    assert await world.run() == IndexReport(claimed=1, indexed=1, deferred=0)
    assert world.documents.of_shop(1) == [] and world.queue.jobs == {}


async def test_처리하는_사이에_다시_바뀌었으면_줄이_남는다():
    world = _World()
    world.source.put(1, "visit", 7, src())
    await world.changed()

    async def changed_again():
        await world.changed()

    world.embedder.during = changed_again
    await world.run()
    [job] = world.queue.jobs.values()
    assert job.generation == 2 and world.queue.due[job.id] == NOW       # 곧 다시 집힌다


async def test_임베딩을_부르는_동안에는_트랜잭션도_잠금도_쥐고_있지_않다():
    world = _World()
    world.source.put(1, "visit", 7, src())
    await world.changed()
    await world.run()
    at = world.journal.index(("embed", 1))
    assert world.journal[at - 1] == ("commit",)                          # 읽은 뒤 닫고 부른다
    assert world.journal[at + 1] == ("lock_family", 1, 1, ())            # 잠금은 그 뒤다
    assert world.journal[at + 1:] == [
        ("lock_family", 1, 1, ()), ("read_source", "visit", 7), ("replace", "visit", 7, 1), ("commit",)]


async def test_컨텍스트는_그_줄의_매장과_시간대이고_권한이_비어_있다():
    world = _World()
    world.shops.timezones = {1: "Asia/Seoul", 2: "Asia/Tokyo"}
    world.source.put(2, "pet", 101, src("pet_memo", 101, "드라이를 무서워해요"))
    world.documents.seed(1, doc("pet_memo", 101, body="다른 매장의 같은 번호"))
    await world.changed("pet", 101, shop_id=2)
    await world.run()
    assert {(c.shop_id, c.timezone, c.member_id, c.role, c.permissions) for c in world.source.seen} == {
        (2, "Asia/Tokyo", 0, "system", frozenset())}
    assert [d.body for d in world.documents.of_shop(2)] == ["드라이를 무서워해요"]
    assert [d.body for d in world.documents.of_shop(1)] == ["다른 매장의 같은 번호"]


async def test_없는_매장의_줄은_문서를_지우고_끝낸다():
    world = _World()
    world.documents.seed(9, doc("care_note", 7))
    world.source.put(9, "visit", 7, src())
    await world.changed(shop_id=9)
    assert await world.run() == IndexReport(claimed=1, indexed=1, deferred=0)
    assert world.documents.of_shop(9) == [] and world.queue.jobs == {} and world.embedder.calls == []


async def test_한_줄이_던져도_다음_줄은_처리하고_던진_줄은_미룬다(caplog):
    world = _World()
    world.source.put(1, "visit", 7, src(body=SECRET))
    world.source.put(1, "visit", 8, src("care_note", 8, "얌전했어요"))
    world.source.fail_for.add(7)
    await world.changed("visit", 7)
    await world.changed("visit", 8)
    with caplog.at_level(logging.DEBUG):
        assert await world.run() == IndexReport(claimed=2, indexed=1, deferred=1)
    assert list(world.stored()) == [("care_note", 8)]
    [job] = world.queue.jobs.values()
    assert (job.ref_id, job.attempts) == (7, 1)
    [record] = [r for r in caplog.records if r.name == "search.indexer"]
    assert "shop_id=1" in record.getMessage() and "visit" in record.getMessage() and "RuntimeError" in record.getMessage()
    assert SECRET not in caplog.text and "원본 읽기 실패" not in caplog.text


async def test_로그에_글이_남지_않는다(caplog):
    world = _World()
    world.source.put(1, "visit", 7, src(body=SECRET))
    world.embedder.down = True
    await world.changed()
    with caplog.at_level(logging.DEBUG):
        await world.run()
    assert SECRET not in caplog.text


async def test_한_번에_정한_수만큼만_집는다():
    world = _World(batch=2)
    for ref in (1, 2, 3):
        world.source.put(1, "visit", ref, src("care_note", ref))
        await world.changed("visit", ref)
    assert (await world.run()).claimed == 2
    assert len(world.queue.jobs) == 1


async def test_색인_시간_제한으로_부른다():
    world = _World()
    seen = []
    original = world.embedder.embed

    async def spy(kind, texts, timeout):
        seen.append(timeout)
        return await original(kind, texts, timeout)

    world.embedder.embed = spy
    world.source.put(1, "visit", 7, src())
    await world.changed()
    await world.run()
    assert seen == [INDEX_TIMEOUT] == [10.0]
