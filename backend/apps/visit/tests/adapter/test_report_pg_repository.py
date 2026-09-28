from datetime import timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOW = kst(9, 28, 15)
WEEK = NOW + timedelta(days=7)
FIRST, SECOND = b"\x01" * 16, b"\x02" * 16


async def _setup(session, **visit_fields):
    return ReportPgRepository(session), await insert_visit(session, kst(9, 28, 14), "completed", **visit_fields)


async def test_만들고_살아_있는_링크로_읽는다(db_session):
    repo, visit_id = await _setup(db_session)
    created = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert (created.visit_id, created.public_id, created.expires_at, created.created_at) == (
        visit_id, FIRST, WEEK, NOW)
    assert (created.revoked_at, created.first_viewed_at, created.created_by_member_id) == (None, None, 11)
    assert await repo.get_live(A, visit_id, NOW) == created


async def test_다른_매장의_방문의_링크는_없는_것이다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert await repo.get_live(B, visit_id, NOW) is None
    assert await repo.live_visit_ids(B, [visit_id], NOW) == set()
    assert await repo.revoke(B, visit_id, NOW) is False
    await repo.close_expired(B, visit_id, WEEK)
    await repo.revoke_for_customer(B, 1, NOW)
    assert (await repo.get_live(A, visit_id, NOW)).revoked_at is None


async def test_기간이_지나면_살아_있지_않지만_공개_조회는_줄을_준다(db_session):
    repo, visit_id = await _setup(db_session)
    created = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert await repo.get_live(A, visit_id, WEEK - timedelta(seconds=1)) == created
    assert await repo.get_live(A, visit_id, WEEK) is None   # 끝나는 바로 그 시각에는 닫혀 있다
    assert (await repo.find(FIRST)).report == created


async def test_기간이_없는_링크는_언제나_살아_있다(db_session):
    repo, visit_id = await _setup(db_session)
    created = await repo.create(A, visit_id, FIRST, None, NOW)
    assert await repo.get_live(A, visit_id, NOW + timedelta(days=3650)) == created


async def test_끊지_않은_줄이_있는데_또_만들면_유일_위반이다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    with pytest.raises(IntegrityError):
        await repo.create(A, visit_id, SECOND, WEEK, NOW)


async def test_기간이_지난_줄을_닫지_않으면_새로_만들_수_없다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    with pytest.raises(IntegrityError):
        await repo.create(A, visit_id, SECOND, None, WEEK)


async def test_기간이_지난_줄을_닫으면_새로_만들_수_있다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    await repo.close_expired(A, visit_id, WEEK)
    created = await repo.create(A, visit_id, SECOND, None, WEEK)
    assert await repo.get_live(A, visit_id, WEEK) == created
    assert (await repo.find(FIRST)).report.revoked_at == WEEK


async def test_기간이_남은_줄은_닫지_않는다(db_session):
    repo, visit_id = await _setup(db_session)
    forever = await repo.create(A, visit_id, FIRST, None, NOW)
    await repo.close_expired(A, visit_id, WEEK)
    assert await repo.get_live(A, visit_id, WEEK) == forever
    other = await insert_visit(db_session, kst(9, 29, 14), "completed")
    dated = await repo.create(A, other, SECOND, WEEK, NOW)
    await repo.close_expired(A, other, WEEK - timedelta(seconds=1))
    assert await repo.get_live(A, other, NOW) == dated


async def test_끊고_새로_만들면_다른_줄이고_옛_줄은_끊긴_채다(db_session):
    repo, visit_id = await _setup(db_session)
    old = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    later = NOW + timedelta(hours=1)
    assert await repo.revoke(A, visit_id, later) is True
    new = await repo.create(A, visit_id, SECOND, WEEK, later)
    assert (new.id != old.id, new.public_id) == (True, SECOND)
    assert await repo.get_live(A, visit_id, later) == new
    assert (await repo.find(FIRST)).report.revoked_at == later


async def test_끊기는_살아_있는_것만_끊는다(db_session):
    repo, visit_id = await _setup(db_session)
    assert await repo.revoke(A, visit_id, NOW) is False   # 링크가 없다
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert await repo.revoke(A, visit_id, WEEK) is False   # 기간이 지났다
    assert (await repo.find(FIRST)).report.revoked_at is None
    assert await repo.revoke(A, visit_id, NOW) is True
    assert await repo.revoke(A, visit_id, NOW) is False   # 이미 끊었다
    assert await repo.get_live(A, visit_id, NOW) is None


async def test_끊기는_그_방문의_링크만_끊는다(db_session):
    repo, visit_id = await _setup(db_session)
    other = await insert_visit(db_session, kst(9, 29, 14), "completed")
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    kept = await repo.create(A, other, SECOND, WEEK, NOW)
    await repo.revoke(A, visit_id, NOW)
    assert await repo.get_live(A, other, NOW) == kept


async def test_익명화는_그_보호자의_끊지_않은_링크를_모두_끊는다(db_session):
    repo, visit_id = await _setup(db_session)
    expired = await insert_visit(db_session, kst(9, 27, 14), "completed")
    revoked = await insert_visit(db_session, kst(9, 26, 14), "completed")
    theirs = await insert_visit(db_session, kst(9, 29, 14), "completed", customer_id=2)
    ids = {v: bytes([n]) * 16 for n, v in enumerate((visit_id, expired, revoked, theirs), start=1)}
    for v, public_id in ids.items():
        await repo.create(A, v, public_id, NOW + timedelta(hours=1) if v == expired else None, NOW)
    await repo.revoke(A, revoked, NOW)
    later = NOW + timedelta(days=1)
    await repo.revoke_for_customer(A, 1, later)
    assert {v: (await repo.find(p)).report.revoked_at for v, p in ids.items()} == {
        visit_id: later, expired: later, revoked: NOW, theirs: None}


async def test_살아_있는_링크가_있는_방문을_질의_하나로_읽는다(db_session, db_engine):
    repo, visit_id = await _setup(db_session)
    expired = await insert_visit(db_session, kst(9, 27, 14), "completed")
    revoked = await insert_visit(db_session, kst(9, 26, 14), "completed")
    forever = await insert_visit(db_session, kst(9, 25, 14), "completed")
    bare = await insert_visit(db_session, kst(9, 24, 14), "completed")
    await repo.create(A, visit_id, b"\x01" * 16, WEEK, NOW)
    await repo.create(A, expired, b"\x02" * 16, NOW + timedelta(minutes=1), NOW)
    await repo.create(A, revoked, b"\x03" * 16, WEEK, NOW)
    await repo.create(A, forever, b"\x04" * 16, None, NOW)
    await repo.revoke(A, revoked, NOW)
    statements = []
    event.listen(db_engine.sync_engine, "before_cursor_execute", lambda *args: statements.append(args[2]))
    found = await repo.live_visit_ids(A, [visit_id, expired, revoked, forever, bare], NOW + timedelta(minutes=1))
    assert found == {visit_id, forever}
    assert len(statements) == 1
    assert await repo.live_visit_ids(A, [], NOW) == set()
    assert len(statements) == 1   # 빈 목록은 묻지 않는다


async def test_공개_조회는_링크와_매장과_방문을_함께_준다(db_session):
    from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
    from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
    from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
    from visit.domain.value_objects.new_visit import NewVisit

    await SchedulePgRepository(db_session).ensure(B)
    bath, trim, *_ = [m.id for m in await MenuPgRepository(db_session).list(B, include_archived=False)]
    [visit] = await VisitPgRepository(db_session).create_many(B, [NewVisit(
        customer_id=1, pet_id=101, starts_at=kst(9, 28, 14), duration_minutes=90, status="reserved",
        started_at=None, menu_ids=(trim, bath), memo=None, created_by_member_id=11)])
    repo = ReportPgRepository(db_session)
    created = await repo.create(B, visit.id, FIRST, WEEK, NOW)
    found = await repo.find(FIRST)
    assert (found.report, found.shop_id, found.visit) == (created, 2, visit)
    assert found.visit.menu_ids == (bath, trim)


async def test_없는_링크는_None_이다(db_session):
    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    assert await repo.find(SECOND) is None


async def test_처음_연_시각은_한_번만_적는다(db_session):
    repo, visit_id = await _setup(db_session)
    other = await insert_visit(db_session, kst(9, 29, 14), "completed")
    created = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    await repo.create(A, other, SECOND, WEEK, NOW)
    opened = NOW + timedelta(minutes=5)
    await repo.mark_viewed(created.id, opened)
    await repo.mark_viewed(created.id, opened + timedelta(hours=1))
    assert (await repo.find(FIRST)).report.first_viewed_at == opened
    assert (await repo.find(SECOND)).report.first_viewed_at is None


async def test_방문을_지우면_링크도_함께_지워진다(db_session):
    from sqlalchemy import delete

    from visit.adapter.outbound.orm.visit_orm import VisitOrm

    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    await db_session.execute(delete(VisitOrm).where(VisitOrm.id == visit_id))
    assert await repo.find(FIRST) is None
