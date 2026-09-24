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


async def test_기록이_있는_방문마다_기록_전체를_한_번에_읽는다(db_session):
    repo, visit_id, bath, _ = await _setup(db_session)
    bare = await insert_visit(db_session, kst(9, 24, 14), "in_progress")
    none = await insert_visit(db_session, kst(9, 25, 14), "in_progress")
    await repo.save(A, _record(visit_id, items=[RecordItem(bath, 1)],
                               media=[RecordMedia(7, "photo", "after", 0), RecordMedia(8, "photo", "before", 0)]))
    await repo.save(A, _record(bare))
    found = await repo.list_many(A, [visit_id, bare, none])
    assert set(found) == {visit_id, bare}
    assert (found[visit_id].media, found[visit_id].items, found[bare].media) == (
        (RecordMedia(8, "photo", "before", 0), RecordMedia(7, "photo", "after", 0)), (RecordItem(bath, 1),), ())
    assert await repo.list_many(B, [visit_id]) == {}
    assert await repo.list_many(A, []) == {}


async def test_사진이_붙은_가장_최근_완료_방문을_아이마다_한_번에(db_session):
    repo, _, _, _ = await _setup(db_session)
    old = await insert_visit(db_session, kst(9, 1, 14), "completed")
    latest = await insert_visit(db_session, kst(9, 10, 14), "completed")
    no_photo = await insert_visit(db_session, kst(9, 20, 14), "completed")
    working = await insert_visit(db_session, kst(9, 22, 14), "in_progress")
    theirs = await insert_visit(db_session, kst(9, 21, 14), "completed", shop_id=2)
    other_pet = await insert_visit(db_session, kst(9, 5, 14), "completed", pet_id=102)
    for visit_id, media_id in ((old, 1), (latest, 2), (working, 3), (theirs, 4), (other_pet, 5)):
        await repo.save(A, _record(visit_id, media=[RecordMedia(media_id, "photo", "after", 0)]))
    await repo.save(A, _record(no_photo))
    assert await repo.latest_with_media(A, [101, 102, 103]) == {101: latest, 102: other_pet}
    assert await repo.latest_with_media(A, []) == {}


async def test_익명화는_그_보호자의_기록_메모만_비운다(db_session):
    repo, visit_id, _, _ = await _setup(db_session)
    other = await insert_visit(db_session, kst(9, 24, 14), "in_progress", customer_id=2)
    await repo.save(A, _record(visit_id, media=[RecordMedia(7, "photo", "after", 0)]))
    await repo.save(A, _record(other))
    await repo.clear_notes(A, 1)
    cleared, kept = await repo.get(A, visit_id), await repo.get(A, other)
    assert (cleared.care_note, cleared.internal_note, len(cleared.media), kept.care_note) == (None, None, 1, "케어")
