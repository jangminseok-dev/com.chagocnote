from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
from visit.domain.entities.visit_record import RecordItem, RecordMedia, VisitRecord
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


def _record(visit_id, version=1, items=(), media=(), weight=None, member=11):
    return VisitRecord(visit_id=visit_id, weight_kg=weight, care_note="케어", internal_note=None,
                       payment_method="cash", total_amount=30_000, items=tuple(items), media=tuple(media),
                       version=version, created_by_member_id=member, updated_by_member_id=member)


async def _setup(session):
    await SchedulePgRepository(session).ensure(A)
    bath, trim, *_ = [m.id for m in await MenuPgRepository(session).list(A, include_archived=False)]
    visit_id = await insert_visit(session, kst(9, 23, 14), "in_progress")
    return VisitRecordPgRepository(session), visit_id, bath, trim


async def test_없으면_넣고_있으면_바꾸고_항목과_미디어는_통째로_바꾼다(db_session):
    repo, visit_id, bath, trim = await _setup(db_session)
    assert await repo.get(A, visit_id) is None
    first = await repo.save(A, _record(visit_id, items=[RecordItem(bath, 30_000)], weight=Decimal("3.2"),
                                       media=[RecordMedia(7, "photo", "after", 0), RecordMedia(8, "photo", "before", 0)]))
    assert (first.version, first.weight_kg, [m.media_id for m in first.media]) == (1, Decimal("3.2"), [8, 7])
    second = await repo.save(A, _record(visit_id, version=2, items=[RecordItem(trim, 50_000)],
                                        media=[RecordMedia(9, "video", "after", 0)], member=12))
    assert (second.version, second.items, second.media) == (2, (RecordItem(trim, 50_000),),
                                                            (RecordMedia(9, "video", "after", 0),))
    assert (second.created_by_member_id, second.updated_by_member_id) == (11, 12)


async def test_다른_매장의_방문의_기록은_없는_것이다(db_session):
    repo, visit_id, _, _ = await _setup(db_session)
    await repo.save(A, _record(visit_id))
    assert await repo.get(B, visit_id) is None


async def test_한_미디어는_한_기록에만_붙는다(db_session):
    repo, visit_id, _, _ = await _setup(db_session)
    other = await insert_visit(db_session, kst(9, 24, 14), "in_progress")
    await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0)]))
    with pytest.raises(IntegrityError):
        await repo.save(A, _record(other, media=[RecordMedia(7, "photo", "after", 0)]))


async def test_지우면_항목과_미디어_연결도_함께_지워진다(db_session):
    repo, visit_id, bath, _ = await _setup(db_session)
    await repo.save(A, _record(visit_id, items=[RecordItem(bath, 1)], media=[RecordMedia(7, "photo", "after", 0)]))
    await repo.delete(A, visit_id)
    assert await repo.get(A, visit_id) is None
    await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0)]))   # 연결이 남았으면 유일 위반
