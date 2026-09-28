"""알림장의 경합 — 실제 두 세션으로 확인한다(막힌 호출을 create_task 로 들고, 앞선 세션이 커밋한 뒤의 결과를 본다)."""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.tests.helpers.profiles import customer_profile, pet_profile
from hub.app.dtos.shop_profile import ShopProfile
from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.app.use_cases.media_library_interactor import MediaLibraryInteractor
from media.tests.helpers.fakes import FakeStorage
from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
from visit.adapter.outbound.pg.report_settings_pg_repository import ReportSettingsPgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
from visit.domain.errors import VisitReportSentError
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeShopProfile
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
PROFILE = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
BLOCKED = 0.5


def _now():
    return kst(9, 24, 10)


def _directory(session):
    return CustomerDirectoryInteractor(CustomerPgRepository(session), PetPgRepository(session),
                                       FamilyBriefPgRepository(session), CustomerSearchPgAdapter(session))


def _library(session):
    return MediaLibraryInteractor(MediaPgRepository(session), FakeStorage(), now=_now)


def _send(session):
    return SendVisitReportInteractor(
        visits=VisitPgRepository(session), records=VisitRecordPgRepository(session),
        settings=ReportSettingsPgRepository(session), reports=ReportPgRepository(session),
        menus=MenuPgRepository(session), directory=_directory(session), library=_library(session),
        shops=FakeShopProfile({1: PROFILE}), now=_now, link_key=bytes(range(32)),
        web_base_url="https://r.example",
    )


def _revert(session, visit_id):
    visits = VisitPgRepository(session)
    return TransitionVisitsInteractor(
        visits, visits, MenuPgRepository(session), ReportPgRepository(session), _directory(session), now=_now,
    ).transition_visits(TransitionVisitsCommand(ctx=SHOP, visit_ids=(visit_id,), action="revert",
                                                cancel_reason=None))


def _delete_record(session, visit_id):
    return DeleteVisitRecordInteractor(
        VisitPgRepository(session), VisitRecordPgRepository(session), ReportPgRepository(session),
        _directory(session), _library(session), now=_now,
    ).delete_visit_record(DeleteVisitRecordCommand(ctx=SHOP, visit_id=visit_id))


def _revoke(session, visit_id):
    return RevokeVisitReportInteractor(
        VisitPgRepository(session), ReportPgRepository(session), _directory(session), now=_now,
    ).revoke_visit_report(RevokeVisitReportCommand(ctx=SHOP, visit_id=visit_id))


async def _recorded_visit(db_session) -> int:
    """케어 메모를 적고 완료한 방문."""
    customer = await CustomerPgRepository(db_session).create(SHOP, customer_profile())
    pet = await PetPgRepository(db_session).add(SHOP, customer.id, pet_profile())
    visit_id = await insert_visit(db_session, kst(9, 23, 14), "completed", customer_id=customer.id, pet_id=pet.id)
    await VisitRecordPgRepository(db_session).save(SHOP, record(visit_id, care_note="눈물 자국"))
    await db_session.commit()
    return visit_id


async def _after(db_session, visit_id):
    """(방문의 상태, 기록이 있는가, 링크마다 살아 있는가)"""
    return (await db_session.execute(text(
        "SELECT v.status, EXISTS (SELECT 1 FROM visit_records r WHERE r.visit_id = v.id),"
        " ARRAY(SELECT l.revoked_at IS NULL FROM visit_reports l WHERE l.visit_id = v.id ORDER BY l.id)"
        " FROM visits v WHERE v.id = :id"), {"id": visit_id})).one()


async def test_같은_방문에_동시에_두_번_보내도_둘_다_성공하고_링크는_하나다(db_engine, db_session):
    """R8 — 고객 행 → 방문 행 잠금을 빼면 늦은 쪽도 '링크 없음'을 읽고 새 줄을 넣으려다 유일 색인에 걸린다."""
    visit_id = await _recorded_visit(db_session)
    command = SendVisitReportCommand(ctx=SHOP, visit_id=visit_id, hidden_media_ids=())

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        early = await _send(first).send_visit_report(command)
        late = asyncio.create_task(_send(second).send_visit_report(command))
        await asyncio.sleep(BLOCKED)
        assert not late.done()
        await first.commit()
        late_sent = await late
        await second.commit()

    assert early.link.status == "live" and late_sent.link == early.link
    rows = (await db_session.execute(
        text("SELECT revoked_at FROM visit_reports WHERE visit_id = :id"), {"id": visit_id})).all()
    assert rows == [(None,)]


@pytest.mark.parametrize("late_call", [_revert, _delete_record])
async def test_보내는_동안_온_되돌리기와_기록_삭제는_기다렸다가_VISIT_REPORT_SENT_로_끝난다(
        db_engine, db_session, late_call):
    """R9 — 링크를 잠그기 전에 읽으면 '링크 없음'을 본 채 기다렸다가, 보낸 방문을 되돌리거나 기록을 지워 버린다."""
    visit_id = await _recorded_visit(db_session)

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as sending, sessions() as second:
        await _send(sending).send_visit_report(
            SendVisitReportCommand(ctx=SHOP, visit_id=visit_id, hidden_media_ids=()))
        late = asyncio.create_task(late_call(second, visit_id))
        await asyncio.sleep(BLOCKED)
        assert not late.done()
        await sending.commit()
        with pytest.raises(VisitReportSentError):
            await late
        await second.rollback()

    assert await _after(db_session, visit_id) == ("completed", True, [True])


async def test_보내는_동안_온_끊기는_기다렸다가_그_링크를_끊는다(db_engine, db_session):
    """끊기가 잠그지 않으면 아직 커밋되지 않은 링크를 보지 못해 REPORT_NOT_FOUND 로 끝나고 링크는 살아 있다."""
    visit_id = await _recorded_visit(db_session)

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as sending, sessions() as revoking:
        await _send(sending).send_visit_report(
            SendVisitReportCommand(ctx=SHOP, visit_id=visit_id, hidden_media_ids=()))
        late = asyncio.create_task(_revoke(revoking, visit_id))
        await asyncio.sleep(BLOCKED)
        assert not late.done()
        await sending.commit()
        await late
        await revoking.commit()

    assert await _after(db_session, visit_id) == ("completed", True, [False])
