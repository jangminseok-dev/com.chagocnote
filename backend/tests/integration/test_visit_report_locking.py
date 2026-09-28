"""알림장 보내기의 경합 — 실제 두 세션으로 확인한다(막힌 호출을 create_task 로 들고, 앞선 세션이 커밋한 뒤의 결과를 본다)."""
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
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeShopProfile
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
PROFILE = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
BLOCKED = 0.5


def _send(session):
    directory = CustomerDirectoryInteractor(CustomerPgRepository(session), PetPgRepository(session),
                                            FamilyBriefPgRepository(session), CustomerSearchPgAdapter(session))
    library = MediaLibraryInteractor(MediaPgRepository(session), FakeStorage(), now=lambda: kst(9, 24, 10))
    return SendVisitReportInteractor(
        visits=VisitPgRepository(session), records=VisitRecordPgRepository(session),
        settings=ReportSettingsPgRepository(session), reports=ReportPgRepository(session),
        menus=MenuPgRepository(session), directory=directory, library=library,
        shops=FakeShopProfile({1: PROFILE}), now=lambda: kst(9, 24, 10), link_key=bytes(range(32)),
        web_base_url="https://r.example",
    )


async def test_같은_방문에_동시에_두_번_보내도_둘_다_성공하고_링크는_하나다(db_engine, db_session):
    """R8 — 고객 행 → 방문 행 잠금을 빼면 늦은 쪽도 '링크 없음'을 읽고 새 줄을 넣으려다 유일 색인에 걸린다."""
    customer = await CustomerPgRepository(db_session).create(SHOP, customer_profile())
    pet = await PetPgRepository(db_session).add(SHOP, customer.id, pet_profile())
    visit_id = await insert_visit(db_session, kst(9, 23, 14), "completed", customer_id=customer.id, pet_id=pet.id)
    await VisitRecordPgRepository(db_session).save(SHOP, record(visit_id, care_note="눈물 자국"))
    await db_session.commit()
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
