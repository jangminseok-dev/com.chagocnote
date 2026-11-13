import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

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


async def test_두_세션이_동시에_처음_연_시각을_적어도_먼저_커밋한_것이_남는다(db_engine, db_session):
    """R10 — '아직 비어 있을 때만'이라는 조건이 없으면 기다리던 쪽이 앞선 시각을 덮어쓴다."""
    repo, visit_id = await _setup(db_session)
    created = await repo.create(A, visit_id, FIRST, WEEK, NOW)
    await db_session.commit()
    early, later = NOW + timedelta(minutes=5), NOW + timedelta(hours=1)

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        await ReportPgRepository(first).mark_viewed(created.id, early)
        late = asyncio.create_task(ReportPgRepository(second).mark_viewed(created.id, later))
        await asyncio.sleep(0.5)
        assert not late.done()
        await first.commit()
        await late
        await second.commit()

    assert (await repo.find(FIRST)).report.first_viewed_at == early


async def test_방문을_지우면_링크도_함께_지워진다(db_session):
    from sqlalchemy import delete

    from visit.adapter.outbound.orm.visit_orm import VisitOrm

    repo, visit_id = await _setup(db_session)
    await repo.create(A, visit_id, FIRST, WEEK, NOW)
    await db_session.execute(delete(VisitOrm).where(VisitOrm.id == visit_id))
    assert await repo.find(FIRST) is None


# --- 보호자용 읽기(GuardianReportRepository) — 쪽 나눔·아이 거르기·보호자만의 방문을 실제 DB 로 고정한다 ----------

from sqlalchemy import text  # noqa: E402


async def _sent(session, repo, starts_at, public_id: int, *, pet_id=101, customer_id=1, record=True) -> tuple[int, int]:
    """starts_at 의 완료 방문에 기록과 알림장을 둔다. (visit_id, report_id)"""
    visit_id = await insert_visit(session, starts_at, "completed", customer_id=customer_id, pet_id=pet_id)
    if record:
        await session.execute(text(
            "INSERT INTO visit_records (visit_id, care_note, created_by_member_id, updated_by_member_id) "
            "VALUES (:visit_id, '메모', 11, 11)"), {"visit_id": visit_id})
    report = await repo.create(A, visit_id, public_id.to_bytes(16, "big"), None, NOW)
    return visit_id, report.id


async def test_보호자용_목록은_최신순이고_before_로_다음_쪽을_빠짐없이_겹침없이_준다(db_session):
    repo = ReportPgRepository(db_session)
    made = [await _sent(db_session, repo, kst(9, day, 14), day) for day in (20, 21, 22, 23, 24)]
    newest_first = [report_id for _, report_id in reversed(made)]

    first = await repo.list_sent(A, 1, pet_id=None, before=None, limit=2)
    assert [s.report.id for s in first] == newest_first[:2]
    last = first[-1].visit
    second = await repo.list_sent(A, 1, pet_id=None, before=(last.starts_at, last.id), limit=2)
    assert [s.report.id for s in second] == newest_first[2:4]
    last = second[-1].visit
    third = await repo.list_sent(A, 1, pet_id=None, before=(last.starts_at, last.id), limit=2)
    assert [s.report.id for s in third] == newest_first[4:]


async def test_같은_시각의_두_방문이_쪽_경계에_걸려도_빠지거나_겹치지_않는다(db_session):
    """가족 두 마리의 같은 날 방문 — 시작 시각이 같으면 방문 ID 로 순서를 가른다."""
    repo = ReportPgRepository(db_session)
    same = kst(9, 22, 14)
    kong = await _sent(db_session, repo, same, 1, pet_id=101)
    dubu = await _sent(db_session, repo, same, 2, pet_id=102)
    older = await _sent(db_session, repo, kst(9, 20, 14), 3)

    first = await repo.list_sent(A, 1, pet_id=None, before=None, limit=1)
    assert [s.report.id for s in first] == [dubu[1]]            # 같은 시각이면 방문 ID 가 큰 쪽이 먼저다
    last = first[-1].visit
    rest = await repo.list_sent(A, 1, pet_id=None, before=(last.starts_at, last.id), limit=5)
    assert [s.report.id for s in rest] == [kong[1], older[1]]


async def test_아이로_거르면_그_아이의_것만이고_보호자만의_방문은_목록에만_있다(db_session):
    repo = ReportPgRepository(db_session)
    kong = await _sent(db_session, repo, kst(9, 20, 14), 1, pet_id=101)
    dubu = await _sent(db_session, repo, kst(9, 21, 14), 2, pet_id=102)
    alone = await _sent(db_session, repo, kst(9, 22, 14), 3, pet_id=None)

    assert [s.report.id for s in await repo.list_sent(A, 1, pet_id=102, before=None, limit=20)] == [dubu[1]]
    everything = await repo.list_sent(A, 1, pet_id=None, before=None, limit=20)
    assert [(s.report.id, s.visit.pet_id) for s in everything] == [(alone[1], None), (dubu[1], 102), (kong[1], 101)]
    assert await repo.pet_ids_with_reports(A, 1) == [101, 102]


async def test_보호자용_읽기는_끊은_것_기록_없는_것_다른_고객_다른_매장의_것을_주지_않는다(db_session):
    repo = ReportPgRepository(db_session)
    mine = await _sent(db_session, repo, kst(9, 20, 14), 1)
    revoked = await _sent(db_session, repo, kst(9, 21, 14), 2)
    await repo.revoke(A, revoked[0], NOW)
    no_record = await _sent(db_session, repo, kst(9, 22, 14), 3, record=False)
    theirs = await _sent(db_session, repo, kst(9, 23, 14), 4, customer_id=2, pet_id=201)

    assert [s.report.id for s in await repo.list_sent(A, 1, pet_id=None, before=None, limit=20)] == [mine[1]]
    assert (await repo.get_sent(A, 1, mine[1])).visit.id == mine[0]
    for report_id in (revoked[1], no_record[1], theirs[1]):
        assert await repo.get_sent(A, 1, report_id) is None
    assert await repo.get_sent(B, 1, mine[1]) is None
    assert await repo.list_sent(B, 1, pet_id=None, before=None, limit=20) == []
    assert await repo.pet_ids_with_reports(A, 2) == [201]
