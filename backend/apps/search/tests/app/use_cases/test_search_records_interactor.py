"""기록 검색 — 글자 후보와 뜻 후보를 합치고, 이름·사진을 허브 포트로 붙인다."""
from datetime import date
from decimal import Decimal

import pytest

from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
from hub.app.dtos.media_urls import MediaUrls
from search.app.dtos.search_records_dto import SearchRecordsQuery
from search.app.ports.output.embedding_port import QUERY_TIMEOUT
from search.app.use_cases.search_records_interactor import SearchRecordsInteractor
from search.domain.entities.search_document import PetScope
from search.domain.errors import SearchQueryError
from search.tests.helpers.builders import candidate, ctx
from search.tests.helpers.fakes import FakeCandidates, FakeEmbedder


class _Directory:
    """CustomerDirectoryPort 의 briefs·first_pets 만. owners {고객: 이름|None}, pets {아이: (고객, 이름|None)}."""

    def __init__(self):
        self.owners = {1: "김민지", 2: "이수진"}
        self.pets = {101: (1, "콩이"), 102: (1, "두부"), 201: (2, "몽이")}
        self.first = {1: 101, 2: 201}
        self.shop_id = 1
        self.calls: list[tuple] = []

    async def briefs(self, ctx, customer_ids, pet_ids):
        self.calls.append(("briefs", sorted(customer_ids), sorted(pet_ids)))
        if ctx.shop_id != self.shop_id:
            return FamilyBriefs(customers={}, pets={})
        return FamilyBriefs(
            customers={c: CustomerBrief(customer_id=c, name=self.owners[c], phone_masked=None)
                       for c in customer_ids if c in self.owners},
            pets={p: PetBrief(pet_id=p, customer_id=self.pets[p][0], name=self.pets[p][1], species="dog",
                              breed="말티즈", weight_kg=Decimal("3.2"), passed_away=False)
                  for p in pet_ids if p in self.pets},
        )

    async def first_pets(self, ctx, customer_ids):
        self.calls.append(("first_pets", tuple(sorted(customer_ids))))
        return {c: self.first[c] for c in customer_ids if c in self.first}


class _Ledger:
    def __init__(self):
        self.covers = {101: 51}
        self.calls: list = []

    async def latest_covers(self, ctx, pet_ids):
        self.calls.append(sorted(pet_ids))
        return {p: m for p, m in self.covers.items() if p in pet_ids}


class _Library:
    def __init__(self):
        self.calls: list = []

    async def read_urls(self, ctx, media_ids):
        self.calls.append(sorted(media_ids))
        return {m: MediaUrls(media_id=m, kind="photo", original_url=f"o{m}", download_url=f"d{m}",
                             display_url=f"s{m}", thumb_url=f"thumb-{m}", width=1, height=1, duration_seconds=None)
                for m in media_ids}


class _World:
    def __init__(self, lexical=(), semantic=()):
        self.candidates = FakeCandidates(lexical, semantic)
        self.embedder, self.directory, self.ledger, self.library = FakeEmbedder(), _Directory(), _Ledger(), _Library()
        self.interactor = SearchRecordsInteractor(
            candidates=self.candidates, embedder=self.embedder, directory=self.directory, ledger=self.ledger,
            library=self.library)

    async def search(self, q="발톱", pet_id=None, shop_id=1):
        return await self.interactor.search_records(SearchRecordsQuery(ctx=ctx(shop_id), q=q, pet_id=pet_id))


async def test_글자와_뜻_후보를_합쳐_결과_줄을_만든다():
    world = _World(
        lexical=[candidate(1, "care_note", visit_id=7, body="발톱을 짧게 깎았어요", happened_on=date(2026, 11, 3))],
        semantic=[candidate(2, "pet_memo", source_id=101, body="손발을 만지면 싫어해요"),
                  candidate(1, "care_note", visit_id=7, body="발톱을 짧게 깎았어요", happened_on=date(2026, 11, 3))],
    )
    result = await world.search("발톱")
    assert result.semantic is True
    first, second = result.items
    assert (first.kind, first.customer_id, first.owner_name, first.pet_id, first.pet_name, first.photo) == (
        "care_note", 1, "김민지", 101, "콩이", "thumb-51")
    assert (first.visit_id, first.open_pet_id, first.date, first.snippet) == (
        7, None, date(2026, 11, 3), "발톱을 짧게 깎았어요")
    assert (second.kind, second.visit_id, second.open_pet_id, second.date) == ("pet_memo", None, 101, None)


async def test_검색어를_다듬어_후보를_묻는다():
    world = _World()
    await world.search("  100%\n짧게 ")
    [lexical] = [c for c in world.candidates.calls if c[0] == "lexical"]
    assert lexical[1:5] == (1, "100% 짧게", "%100\\% 짧게%", None)
    assert world.embedder.calls == [("query", ["100% 짧게"])]
    [semantic] = [c for c in world.candidates.calls if c[0] == "semantic"]
    assert semantic[2] == FakeEmbedder.vector_of("100% 짧게")


@pytest.mark.parametrize("q", ["", "가", "  가  ", "가" * 101])
async def test_검색어가_맞지_않으면_아무것도_묻지_않고_거절한다(q):
    world = _World()
    with pytest.raises(SearchQueryError):
        await world.search(q)
    assert world.candidates.calls == [] and world.embedder.calls == [] and world.directory.calls == []


async def test_임베딩을_못_받으면_글자_후보만으로_답한다():
    world = _World(lexical=[candidate(1, visit_id=7)], semantic=[candidate(2, "pet_memo", source_id=101)])
    world.embedder.down = True
    result = await world.search()
    assert result.semantic is False and [i.kind for i in result.items] == ["care_note"]
    assert [c[0] for c in world.candidates.calls] == ["lexical"]


async def test_질의_시간_제한으로_임베딩을_부른다():
    world = _World()
    seen = []
    original = world.embedder.embed

    async def spy(kind, texts, timeout):
        seen.append(timeout)
        return await original(kind, texts, timeout)

    world.embedder.embed = spy
    await world.search()
    assert seen == [QUERY_TIMEOUT] == [1.5]


async def test_아이로_좁히면_그_아이와_보호자의_범위로_묻는다():
    world = _World()
    await world.search(pet_id=102)
    scopes = {c[4] if c[0] == "lexical" else c[3] for c in world.candidates.calls}
    assert scopes == {PetScope(pet_id=102, customer_id=1)}


async def test_이_매장에_없는_아이로_좁히면_빈_결과이고_아무것도_묻지_않는다():
    world = _World(lexical=[candidate(1)])
    for pet_id, shop_id in ((999, 1), (101, 2)):
        result = await world.search(pet_id=pet_id, shop_id=shop_id)
        assert result.items == [] and result.semantic is False
    assert world.candidates.calls == [] and world.embedder.calls == []


async def test_같은_방문의_글은_한_줄로_접는다():
    world = _World(lexical=[candidate(1, "care_note", visit_id=7), candidate(2, "internal_note", visit_id=7),
                            candidate(3, "visit_memo", visit_id=8)])
    assert [(i.kind, i.visit_id) for i in (await world.search()).items] == [("care_note", 7), ("visit_memo", 8)]


async def test_결과는_서른_줄까지다():
    world = _World(lexical=[candidate(i, "pet_memo", source_id=101) for i in range(1, 41)])
    assert len((await world.search()).items) == 30


async def test_보호자_메모는_아이_없이_보호자_이름으로_나오고_열_아이를_알려_준다():
    world = _World(lexical=[candidate(1, "customer_memo", source_id=2, customer_id=2, pet_id=None, body="문자 선호"),
                            candidate(2, "customer_memo", source_id=3, customer_id=3, pet_id=None)])
    world.directory.owners[3] = "박지호"          # 아이가 없는 보호자
    first, second = (await world.search("문자")).items
    assert (first.owner_name, first.pet_id, first.pet_name, first.photo, first.open_pet_id) == (
        "이수진", None, None, None, 201)
    assert (second.owner_name, second.open_pet_id) == ("박지호", None)
    assert ("first_pets", (2, 3)) in world.directory.calls


async def test_보호자만의_방문은_아이_없이_방문으로_간다():
    world = _World(lexical=[candidate(1, "visit_memo", visit_id=9, pet_id=None, body="상담만")])
    [item] = (await world.search("상담")).items
    assert (item.pet_id, item.owner_name, item.visit_id, item.open_pet_id) == (None, "김민지", 9, None)


async def test_지병은_그_아이를_연다():
    world = _World(lexical=[candidate(1, "condition_note", source_id=41, pet_id=102, body="심장 질환")])
    [item] = (await world.search("심장")).items
    assert (item.pet_name, item.open_pet_id, item.visit_id, item.photo) == ("두부", 102, None, None)


async def test_익명화했거나_없어진_것이_걸리면_그_줄을_뺀다():
    """색인기가 지우기 전의 짧은 틈 — 이름 없는 줄을 보여 주지 않는다."""
    world = _World(lexical=[
        candidate(1, "care_note", visit_id=7, customer_id=1, pet_id=101),
        candidate(2, "care_note", visit_id=8, customer_id=2, pet_id=201),      # 보호자가 익명화됐다
        candidate(3, "pet_memo", source_id=999, customer_id=1, pet_id=999),    # 아이가 없다
        candidate(4, "care_note", visit_id=9, customer_id=7, pet_id=101),      # 보호자가 없다
    ])
    world.directory.owners[2] = None
    world.directory.pets[201] = (2, None)
    assert [i.visit_id for i in (await world.search()).items] == [7]


async def test_이름과_사진은_줄_수와_상관없이_한_번씩만_묻는다():
    rows = [candidate(i, "care_note", visit_id=i, customer_id=1 + i % 2, pet_id=(101, 201)[i % 2]) for i in range(1, 21)]
    world = _World(lexical=rows)
    await world.search()
    assert world.directory.calls == [("briefs", [1, 2], [101, 201])]       # 보호자 메모가 없으면 first_pets 는 안 부른다
    assert world.ledger.calls == [[101, 201]] and world.library.calls == [[51]]


async def test_걸린_것이_없으면_이름도_사진도_묻지_않는다():
    world = _World()
    result = await world.search()
    assert result.items == [] and result.semantic is True
    assert world.directory.calls == [] and world.ledger.calls == [] and world.library.calls == []


async def test_걸린_문장은_검색어_자리로_자른다():
    body = "가" * 100 + "발톱을 짧게" + "나" * 100
    world = _World(lexical=[candidate(1, visit_id=7, body=body)])
    [item] = (await world.search("발톱")).items
    assert "발톱을 짧게" in item.snippet and len(item.snippet) == 82
