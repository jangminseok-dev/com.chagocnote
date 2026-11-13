from visit.app.services.pet_cards import PetCard, pet_cards, showable_pets
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeRecords, FakeVisits


class _World:
    def __init__(self):
        self.directory, self.visits, self.library = FakeDirectory(), FakeVisits(), FakeLibrary()
        self.records = FakeRecords(self.visits)
        self.directory.family(1, pets=(101, 102, 103))

    def photo(self, pet_id, media_id, day=1, kind="photo", phase="after"):
        visit = self.visits.seed(pet_id=pet_id, starts_at=kst(10, day, 10), status="completed",
                                 started_at=kst(10, day, 10), completed_at=kst(10, day, 12))
        self.library.add(media_id, kind=kind, attached=True)
        self.records.seed(record(visit.id, media=((media_id, kind, phase, 0),)))

    async def cards(self, ids, shop_id=1):
        pets = await showable_pets(ctx(shop_id=shop_id), ids, self.directory)
        return await pet_cards(ctx(shop_id=shop_id), pets, ids, self.records, self.library)


async def test_이름과_가장_최근_사진의_썸네일을_준다():
    w = _World()
    w.photo(101, 51, day=1)
    w.photo(101, 52, day=5)          # 더 최근의 방문
    assert await w.cards([101, 102]) == {
        101: PetCard(pet_id=101, name="아이101", photo_url="t/52"),
        102: PetCard(pet_id=102, name="아이102", photo_url=None),
    }


async def test_익명화한_고객의_아이와_지운_아이와_다른_매장의_아이는_빠진다():
    w = _World()
    w.directory.pet_names[102] = None
    w.directory.family(5, pets=(501,), shop_id=2)
    w.photo(102, 51)
    assert sorted(await w.cards([101, 102, 999, 501])) == [101]
    assert await showable_pets(ctx(), [], w.directory) == {}
    assert await w.cards([]) == {}


async def test_무지개다리를_건넌_아이도_카드가_있다():
    w = _World()
    w.directory.family(2, pets=(201,), passed=(201,))
    assert sorted(await w.cards([201])) == [201]


async def test_같은_아이를_여러_번_넘겨도_한_번만_나온다():
    w = _World()
    assert sorted(await w.cards([101, 101, 102, 101])) == [101, 102]
