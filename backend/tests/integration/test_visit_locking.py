"""visit 의 경합 — 실제 두 세션으로 확인한다.

막힌 호출을 create_task 로 들고 있다가, 앞선 세션이 커밋한 뒤의 결과를 본다(결정 기록 003 의 교훈).
판별은 '기다렸다'와 '커밋 뒤의 결과' 두 단언이 함께 한다. 테스트마다 어느 코드를 빼면 실패하는지 적었다.
"""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.domain.errors import CustomerHasUpcomingVisitsError
from customer.tests.helpers.profiles import customer_profile, pet_profile
from hub.app.errors import FamilyNotFoundError
from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
from visit.app.dtos.register_visit_dto import RegisterVisitCommand
from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
from visit.tests.helpers.fakes import FakeEvents
from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
from visit.domain.errors import VisitDuplicateError, VisitStateConflictError
from visit.tests.helpers.builders import ctx, kst
from tests.integration.support import NoGuardians, NoSearchIndex

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
NOW = kst(9, 23, 15)
BLOCKED = 0.5   # 이만큼 기다려도 끝나지 않으면 잠금에서 기다리는 것으로 본다


def _directory(session):
    return CustomerDirectoryInteractor(
        CustomerPgRepository(session), PetPgRepository(session), FamilyBriefPgRepository(session),
        CustomerSearchPgAdapter(session),
    )


def _register(session, customer_id, pet_ids, starts_at=kst(10, 2, 14)):
    visits = VisitPgRepository(session)
    interactor = RegisterVisitInteractor(
        visits, visits, MenuPgRepository(session), SchedulePgRepository(session),
        _directory(session), events=FakeEvents(), now=lambda: NOW,
    )
    return interactor.register_visit(RegisterVisitCommand(
        ctx=SHOP, customer_id=customer_id, pet_ids=tuple(pet_ids), starts_at=starts_at, duration_minutes=None,
        menu_ids=(), memo=None, walk_in=False,
    ))


def _transition(session, visit_ids, action, reason=None):
    visits = VisitPgRepository(session)
    interactor = TransitionVisitsInteractor(
        visits, visits, MenuPgRepository(session), ReportPgRepository(session), _directory(session),
        events=FakeEvents(), now=lambda: NOW,
    )
    return interactor.transition_visits(TransitionVisitsCommand(
        ctx=SHOP, visit_ids=tuple(visit_ids), action=action, cancel_reason=reason,
    ))


def _anonymize(session, customer_id):
    ledger = VisitLedgerInteractor(VisitPgRepository(session), VisitRecordPgRepository(session),
                                   ReportPgRepository(session), now=lambda: NOW)
    return DeleteCustomerInteractor(CustomerPgRepository(session), CustomerSearchPgAdapter(session), ledger, NoGuardians(), index=NoSearchIndex()) \
        .delete_customer(DeleteCustomerCommand(ctx=SHOP, customer_id=customer_id))


async def _still_waiting(task) -> bool:
    await asyncio.sleep(BLOCKED)
    return not task.done()


async def _family(factory, pet_names=("콩이",)):
    async with factory() as setup:
        customer = await CustomerPgRepository(setup).create(SHOP, customer_profile())
        pets = [await PetPgRepository(setup).add(SHOP, customer.id, pet_profile(name=n)) for n in pet_names]
        await CustomerSearchPgAdapter(setup).rebuild_search_entry(SHOP, customer.id)
        await SchedulePgRepository(setup).ensure(SHOP)
        await setup.commit()
    return customer.id, [p.id for p in pets]


async def _scalar(factory, sql, **params):
    async with factory() as check:
        return (await check.execute(text(sql), params)).scalar_one()


async def test_익명화가_고객을_쥔_동안_예약은_기다리고_뒤에는_404_다(db_engine):
    """V3 — 방문 표에는 고객으로 가는 외래 키가 없다. 가족 잠금(lock_family)이 없으면 예약이 기다리지 않고
    들어가, 익명화한 고객에게 앞으로의 예약이 생긴다. RegisterVisitInteractor 의 lock_family 호출을 빼면 실패한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong,) = await _family(factory)

    async with factory() as deleting, factory() as booking:
        await _anonymize(deleting, customer_id)
        book = asyncio.create_task(_register(booking, customer_id, [kong]))
        assert await _still_waiting(book)

        await deleting.commit()
        with pytest.raises(FamilyNotFoundError):   # customer 의 오류가 아니라 허브 오류로 나온다
            await book
        await booking.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM visits") == 0


async def test_예약이_고객을_쥔_동안_익명화는_기다리고_뒤에는_409_다(db_engine):
    """V3 반대 방향 — 예약의 가족 잠금이 커밋될 때까지 익명화가 기다렸다가 그 예약을 보고 막는다.
    CustomerDirectoryInteractor.lock_family 의 lock_active 를 get_active 로 바꾸면(잠그지 않으면) 익명화가
    기다리지 않고 아직 커밋 전인 예약을 못 본 채 지나가 실패한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong,) = await _family(factory)

    async with factory() as booking, factory() as deleting:
        await _register(booking, customer_id, [kong])
        anonymize = asyncio.create_task(_anonymize(deleting, customer_id))
        assert await _still_waiting(anonymize)

        await booking.commit()
        with pytest.raises(CustomerHasUpcomingVisitsError):
            await anonymize
        await deleting.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM customers WHERE deleted_at IS NULL") == 1
    assert await _scalar(factory, "SELECT count(*) FROM visits") == 1


async def test_같은_예약을_두_기기가_동시에_잡으면_하나만_된다(db_engine):
    """V5 — 늦은 쪽은 고객 잠금에서 기다렸다가 유일 색인에 걸려 VISIT_DUPLICATE 를 받는다.
    uq_visits_pet_start_active 를 일반 색인으로 바꾸면 둘 다 들어가 실패한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong,) = await _family(factory)

    async with factory() as first, factory() as second:
        await _register(first, customer_id, [kong])
        late = asyncio.create_task(_register(second, customer_id, [kong]))
        assert await _still_waiting(late)

        await first.commit()
        with pytest.raises(VisitDuplicateError):
            await late
        await second.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM visits") == 1


async def test_두_기기가_같은_방문에_완료와_노쇼를_누르면_늦은_쪽은_409_다(db_engine):
    """V4 — 늦은 쪽은 잠금에서 기다렸다가 다시 읽은 '완료'를 보고 거절한다.
    잠금이 둘(고객 행, 방문 행) 있어 하나만 빼면 다른 하나가 막는다 — lock_visits 의 lock_family 호출과
    VisitPgRepository.lock 의 with_for_update 를 **둘 다** 빼면 늦은 쪽이 옛 '예약됨'을 보고 노쇼로 덮어 실패한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong,) = await _family(factory)
    async with factory() as setup:
        [visit] = (await _register(setup, customer_id, [kong], starts_at=kst(9, 23, 13))).visits
        await setup.commit()

    async with factory() as first, factory() as second:
        await _transition(first, [visit.visit_id], "complete")
        late = asyncio.create_task(_transition(second, [visit.visit_id], "no_show"))
        assert await _still_waiting(late)

        await first.commit()
        with pytest.raises(VisitStateConflictError):
            await late
        await second.rollback()

    assert await _scalar(factory, "SELECT status FROM visits") == "completed"
    assert await _scalar(factory, "SELECT last_visit_at FROM customer_search_entries") == kst(9, 23, 13)
