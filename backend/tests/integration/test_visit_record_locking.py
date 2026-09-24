"""기록 쓰기의 경합 — 실제 두 세션으로 확인한다(막힌 호출을 create_task 로 들고, 앞선 세션이 커밋한 뒤의 결과를 본다)."""
import asyncio
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.tests.helpers.profiles import customer_profile, pet_profile
from media.adapter.outbound.pg.media_pg_repository import MediaPgRepository
from media.app.use_cases.media_library_interactor import MediaLibraryInteractor
from media.tests.helpers.fakes import FakeStorage
from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
from visit.app.dtos.put_visit_record_dto import PutVisitRecordCommand
from visit.app.use_cases.put_visit_record_interactor import PutVisitRecordInteractor
from visit.domain.errors import RecordVersionConflictError
from visit.domain.value_objects.record_input import RecordInput
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
BLOCKED = 0.5


def _put(session):
    visits = VisitPgRepository(session)
    directory = CustomerDirectoryInteractor(CustomerPgRepository(session), PetPgRepository(session),
                                            FamilyBriefPgRepository(session), CustomerSearchPgAdapter(session))
    library = MediaLibraryInteractor(MediaPgRepository(session), FakeStorage(), now=lambda: kst(9, 23, 15))
    return PutVisitRecordInteractor(visits, visits, VisitRecordPgRepository(session), MenuPgRepository(session),
                                    directory, library)


def _record(note):
    return RecordInput(weight_kg=Decimal("3.4"), care_note=note, internal_note=None, payment_method=None,
                       total_amount=None, items=(), media=())


async def test_같은_버전으로_동시에_두_번_쓰면_늦은_쪽은_RECORD_VERSION_CONFLICT(db_engine, db_session):
    """고객 행 → 방문 행 잠금을 빼면 늦은 쪽도 '기록 없음'을 읽고 덮어써 앞선 쪽의 기록이 사라진다."""
    customer = await CustomerPgRepository(db_session).create(SHOP, customer_profile())
    pet = await PetPgRepository(db_session).add(SHOP, customer.id, pet_profile())
    visit_id = await insert_visit(db_session, kst(9, 23, 14), "in_progress", customer_id=customer.id, pet_id=pet.id)
    await db_session.commit()

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        saved = await _put(first).put_visit_record(
            PutVisitRecordCommand(ctx=SHOP, visit_id=visit_id, version=None, record=_record("앞선 기기")))
        late = asyncio.create_task(_put(second).put_visit_record(
            PutVisitRecordCommand(ctx=SHOP, visit_id=visit_id, version=None, record=_record("늦은 기기"))))
        await asyncio.sleep(BLOCKED)
        assert not late.done()
        await first.commit()
        with pytest.raises(RecordVersionConflictError):
            await late
    assert (saved.version, saved.care_note) == (1, "앞선 기기")
