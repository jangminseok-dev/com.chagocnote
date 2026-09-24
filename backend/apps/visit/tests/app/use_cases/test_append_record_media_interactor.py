from dataclasses import replace
from decimal import Decimal

import pytest

from hub.app.errors import MediaClaimNotReadyError
from visit.app.dtos.append_record_media_dto import AppendRecordMediaCommand
from visit.app.use_cases.append_record_media_interactor import AppendRecordMediaInteractor
from visit.domain.entities.visit_record import RecordMedia, VisitRecord
from visit.domain.errors import RecordMediaLimitError, VisitNoRecordYetError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeMenus, FakeRecords, FakeVisits, Journal


class _World:
    def __init__(self, status="in_progress"):
        self.journal = Journal()
        self.visits = FakeVisits(self.journal)
        self.directory = FakeDirectory(self.journal)
        self.directory.family(1, pets=(101,))
        self.records = FakeRecords(self.visits, self.journal)
        self.library = FakeLibrary(self.journal)
        self.visit = self.visits.seed(status=status, started_at=kst(9, 23, 14))
        self.interactor = AppendRecordMediaInteractor(self.visits, self.records, FakeMenus(), self.directory,
                                                      self.library)

    async def append(self, media_id, phase="before"):
        return await self.interactor.append_record_media(
            AppendRecordMediaCommand(ctx=ctx(member_id=12), visit_id=self.visit.id, media_id=media_id, phase=phase))

    def existing(self, media, version=3):
        return self.records.seed(VisitRecord(
            visit_id=self.visit.id, weight_kg=Decimal("3.4"), care_note="케어", internal_note=None,
            payment_method="cash", total_amount=30_000, items=(), media=tuple(media), version=version,
            created_by_member_id=7, updated_by_member_id=7))


async def test_기록이_없으면_빈_기록을_버전_1_로_만들며_붙인다():
    w = _World()
    w.library.add(51)
    view = await w.append(51)
    assert (view.version, [(m.media_id, m.phase, m.sort_order) for m in view.media]) == (1, [(51, "before", 0)])
    assert (view.total_amount, w.records.rows[w.visit.id].created_by_member_id) == (None, 12)
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "claim", "save_record"]


async def test_있는_기록은_다른_칸을_그대로_두고_버전을_올린다():
    w = _World()
    w.library.add(51, attached=True)
    w.library.add(52, kind="video")
    w.existing([RecordMedia(51, "photo", "after", 0)])
    view = await w.append(52, "after")
    assert view.version == 4
    assert [(m.media_id, m.sort_order) for m in view.media] == [(51, 0), (52, 1)]
    kept = w.records.rows[w.visit.id]
    assert (kept.total_amount, kept.weight_kg, kept.created_by_member_id) == (30_000, Decimal("3.4"), 7)


async def test_이미_붙은_미디어면_아무것도_바꾸지_않는다():
    w = _World()
    w.library.add(51, attached=True)
    w.existing([RecordMedia(51, "photo", "before", 0)])
    view = await w.append(51)
    assert view.version == 3
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits"]


async def test_시작하지_않은_방문이나_준비_전_미디어는_거절한다():
    w = _World()
    w.visits.rows[w.visit.id] = replace(w.visit, status="reserved")
    with pytest.raises(VisitNoRecordYetError):
        await w.append(51)
    w = _World()
    w.library.add(51, ready=False)
    with pytest.raises(MediaClaimNotReadyError):
        await w.append(51)


async def test_영상은_세_편까지다():
    w = _World()
    for i in (61, 62, 63, 64):
        w.library.add(i, kind="video", attached=i != 64)
    w.existing([RecordMedia(i, "video", "after", i - 61) for i in (61, 62, 63)])
    with pytest.raises(RecordMediaLimitError):
        await w.append(64)
