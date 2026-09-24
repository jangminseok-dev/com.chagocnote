from dataclasses import replace
from decimal import Decimal

import pytest

from hub.app.errors import FamilyNotFoundError, MediaClaimAlreadyAttachedError
from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.use_cases.put_visit_record_interactor import PutVisitRecordInteractor
from visit.domain.entities.visit_record import RecordItem, RecordMedia, VisitRecord
from visit.domain.errors import (
    MenuNotAvailableError,
    RecordMediaLimitError,
    RecordSalesForbiddenError,
    RecordVersionConflictError,
    VisitNoRecordYetError,
    VisitNotFoundError,
)
from visit.domain.value_objects.record_input import MediaPlacement, RecordInput
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeVisits, Journal


class _World:
    def __init__(self, status="in_progress"):
        self.journal = Journal()
        self.visits = FakeVisits(self.journal)
        self.directory = FakeDirectory(self.journal)
        self.directory.family(1, pets=(101,))
        self.records = FakeRecords(self.visits, self.journal)
        self.menus = FakeMenus(self.journal)
        self.library = FakeLibrary(self.journal)
        self.visit = self.visits.seed(status=status, started_at=kst(9, 23, 14) if status != "reserved" else None)
        self.bath = self.menus.seed("목욕", price=30_000)
        self.interactor = PutVisitRecordInteractor(self.visits, self.visits, self.records, self.menus,
                                                   self.directory, self.library)

    async def put(self, record, version=None, context=None):
        return await self.interactor.put_visit_record(
            PutVisitRecordCommand(ctx=context or ctx(), visit_id=self.visit.id, version=version, record=record))

    def existing(self, media=(), version=2, **fields):
        return self.records.seed(VisitRecord(
            visit_id=self.visit.id, weight_kg=None, care_note="옛 메모", internal_note=None, payment_method=None,
            total_amount=None, items=(), media=tuple(media), version=version, created_by_member_id=7,
            updated_by_member_id=7, **fields))


def record(weight=None, items=(), media=(), total=None, payment=None, care="눈물 자국 관리"):
    return RecordInput(weight_kg=weight, care_note=care, internal_note="예민함", payment_method=payment,
                       total_amount=total, items=tuple(items), media=tuple(media))


def at(media_id, phase="after", order=0):
    return MediaPlacement(media_id=media_id, phase=phase, sort_order=order)


async def test_처음_쓰면_버전_1_이고_잠근_뒤_가져가고_저장하고_몸무게를_넘긴다():
    w = _World()
    w.library.add(51)
    w.library.add(52, kind="video")
    view = await w.put(record(Decimal("3.4"), [RecordItem(w.bath.id, 28_000)], [at(51), at(52, "before")],
                              total=28_000, payment="card"))
    assert (view.version, view.total_amount, view.payment_method, view.weight_kg) == (1, 28_000, "card", Decimal("3.4"))
    assert [(i.name, i.amount) for i in view.items] == [("목욕", 28_000)]
    assert [(m.media_id, m.kind, m.phase, m.thumb_url) for m in view.media] == [
        (51, "photo", "after", "t/51"), (52, "video", "before", "t/52")]
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "claim", "release", "save_record",
                                         "set_pet_weight"]
    assert w.records.rows[w.visit.id].created_by_member_id == 11


async def test_다시_쓰면_버전이_오르고_남은_사진은_다시_가져가지_않고_빠진_사진은_놓는다():
    w = _World()
    for i in (51, 52, 53):
        w.library.add(i, attached=i in (51, 52))
    w.existing(media=[RecordMedia(51, "photo", "after", 0), RecordMedia(52, "photo", "after", 1)])
    view = await w.put(record(media=[at(52, order=0), at(53, order=1)]), version=2)
    assert view.version == 3
    assert ("claim", [53]) in w.journal and ("release", [51]) in w.journal
    assert w.records.rows[w.visit.id].created_by_member_id == 7   # 처음 쓴 사람은 그대로


async def test_돈_칸은_sales_write_가_없으면_잠그기_전에_403():
    w = _World()
    no_sales = replace(ctx(role="staff"), permissions=frozenset({"record:write"}))
    for wanted in (record(total=0), record(items=[RecordItem(1, 0)]), record(payment="cash")):
        with pytest.raises(RecordSalesForbiddenError):
            await w.put(wanted, context=no_sales)
    assert w.journal == []
    assert (await w.put(record(Decimal("3.1")), context=no_sales)).version == 1   # 돈 칸이 없으면 된다


@pytest.mark.parametrize("status", ["reserved", "canceled", "no_show"])
async def test_시작하지_않은_방문은_VISIT_NO_RECORD_YET(status):
    w = _World(status="reserved")
    w.visits.rows[w.visit.id] = replace(w.visit, status=status)
    with pytest.raises(VisitNoRecordYetError):
        await w.put(record())
    assert "save_record" not in [e[0] for e in w.journal]


async def test_버전이_어긋나면_아무것도_가져가지_않는다():
    w = _World()
    w.library.add(51)
    w.existing(version=4)
    for version in (None, 3):
        with pytest.raises(RecordVersionConflictError):
            await w.put(record(media=[at(51)]), version=version)
    assert "claim" not in [e[0] for e in w.journal]


async def test_다른_매장의_메뉴는_422_MENU_NOT_FOUND_보관한_메뉴는_된다():
    w = _World()
    theirs = w.menus.seed("남의 메뉴", shop_id=2)
    with pytest.raises(MenuNotAvailableError):
        await w.put(record(items=[RecordItem(theirs.id, 1000)]))
    old = w.menus.seed("옛 메뉴", archived=True)
    assert [i.name for i in (await w.put(record(items=[RecordItem(old.id, 1000)]))).items] == ["옛 메뉴"]


async def test_한도를_넘으면_거절한다():
    w = _World()
    for i in range(1, 32):
        w.library.add(i)
    with pytest.raises(RecordMediaLimitError):
        await w.put(record(media=[at(i, order=i) for i in range(1, 32)]))
    assert "save_record" not in [e[0] for e in w.journal]


async def test_다른_기록에_붙은_미디어는_허브_오류가_그대로_나간다():
    w = _World()
    w.library.add(51, attached=True)
    with pytest.raises(MediaClaimAlreadyAttachedError):
        await w.put(record(media=[at(51)]))


async def test_옛_방문의_기록을_고치면_현재_몸무게는_그대로다():
    w = _World(status="completed")
    w.visits.seed(status="completed", starts_at=kst(9, 30, 14))   # 더 최근에 미용한 방문
    await w.put(record(Decimal("2.9")))
    assert "set_pet_weight" not in [e[0] for e in w.journal]


async def test_익명화한_고객과_다른_매장의_방문은_쓸_수_없다():
    w = _World()
    w.directory.families.clear()
    with pytest.raises(FamilyNotFoundError):
        await w.put(record())
    with pytest.raises(VisitNotFoundError):
        await w.put(record(), context=ctx(shop_id=2))
