"""customer 의 경합 — 실제 두 세션으로 확인한다.

막힌 호출을 create_task 로 들고 있다가, 앞선 세션이 커밋한 뒤의 결과를 본다(결정 기록 003 의 교훈).
판별은 '기다렸다'와 '커밋 뒤의 결과' 두 단언이 함께 한다. 외래 키의 암묵적 잠금이나 검색 줄의 행 잠금
때문에 잠금 코드가 없어도 기다릴 수 있으므로, 기다림만으로는 판별하지 않는다.
"""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
from customer.adapter.outbound.pg.consent_form_pg_repository import ConsentFormPgRepository
from customer.adapter.outbound.pg.consent_signature_pg_repository import ConsentSignaturePgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.dtos.delete_pet_dto import DeletePetCommand
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.use_cases.add_pet_interactor import AddPetInteractor
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
from customer.app.use_cases.register_customer_interactor import RegisterCustomerInteractor
from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenError, LastPetError
from customer.tests.helpers.fakes import today
from customer.tests.helpers.inputs import customer_input, pet_input
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile
from visit.adapter.outbound.pg.report_pg_repository import ReportPgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.adapter.outbound.pg.visit_record_pg_repository import VisitRecordPgRepository
from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
from visit.domain.services.visit_schedule import utc_now
from tests.integration.support import NoEvents, NoGuardians, NoSearchIndex

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
BLOCKED = 0.5   # 이만큼 기다려도 끝나지 않으면 잠금에서 기다리는 것으로 본다


def _repos(session):
    return (CustomerPgRepository(session), PetPgRepository(session),
            ConditionTypePgRepository(session), CustomerSearchPgAdapter(session))


def _consent(session) -> dict:
    """서류(⑪)의 저장소 — 익명화·반려동물 삭제가 함께 정리한다."""
    return dict(forms=ConsentFormPgRepository(session), signatures=ConsentSignaturePgRepository(session), now=utc_now)


def _ledger(session):
    """customer 유스케이스가 묻는 방문 장부 — 진입점이 꽂는 것과 같은 실제 구현(visit)."""
    return VisitLedgerInteractor(VisitPgRepository(session), VisitRecordPgRepository(session),
                                 ReportPgRepository(session), now=utc_now)


def _register(session, name):
    customers, pets, types, search = _repos(session)
    return RegisterCustomerInteractor(customers, pets, types, search, today, events=NoEvents()).register_customer(
        RegisterCustomerCommand(ctx=SHOP, customer=customer_input(name=name), pet=pet_input())
    )


async def _still_waiting(task) -> bool:
    await asyncio.sleep(BLOCKED)
    return not task.done()


async def _family(factory, pet_names=("콩이",)):
    async with factory() as setup:
        customer = await CustomerPgRepository(setup).create(SHOP, customer_profile())
        pets = [await PetPgRepository(setup).add(SHOP, customer.id, pet_profile(name=n)) for n in pet_names]
        await CustomerSearchPgAdapter(setup).rebuild_search_entry(SHOP, customer.id)
        await setup.commit()
    return customer.id, [p.id for p in pets]


async def _scalar(factory, sql, **params):
    async with factory() as check:
        return (await check.execute(text(sql), params)).scalar_one()


async def test_같은_번호의_동시_등록은_하나만_성공하고_늦은_쪽은_409_다(db_engine):
    """C2 — 늦은 쪽은 유일 색인에서 앞선 쪽의 커밋을 기다렸다가 CUSTOMER_PHONE_TAKEN 을 받는다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as first, factory() as second:
        await _register(first, "먼저 온 사람")
        late = asyncio.create_task(_register(second, "늦게 온 사람"))
        assert await _still_waiting(late)

        await first.commit()
        with pytest.raises(CustomerPhoneTakenError):
            await late
        await second.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM customers") == 1
    assert await _scalar(factory, "SELECT name FROM customers") == "먼저 온 사람"
    assert await _scalar(factory, "SELECT count(*) FROM customer_search_entries") == 1


async def test_익명화가_고객을_쥔_동안_반려동물_추가는_기다리고_뒤에는_404_다(db_engine):
    """C14 — 잠금이 없으면 익명화한 고객에게 이름 있는 반려동물이 붙고 검색 줄이 되살아난다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, _ = await _family(factory)

    async with factory() as deleting, factory() as adding:
        customers, _, _, search = _repos(deleting)
        await DeleteCustomerInteractor(customers, search, _ledger(deleting), NoGuardians(), index=NoSearchIndex(), **_consent(deleting)).delete_customer(
            DeleteCustomerCommand(ctx=SHOP, customer_id=customer_id)
        )
        customers, pets, types, search = _repos(adding)
        add = asyncio.create_task(AddPetInteractor(customers, pets, types, search, today, events=NoEvents()).add_pet(
            AddPetCommand(ctx=SHOP, customer_id=customer_id, pet=pet_input(name="두부"))
        ))
        assert await _still_waiting(add)

        await deleting.commit()
        with pytest.raises(CustomerNotFoundError):
            await add
        await adding.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM pets WHERE name IS NOT NULL") == 0
    assert await _scalar(factory, "SELECT count(*) FROM customer_search_entries") == 0


async def test_lock_owner가_고객_행을_쥔_동안_다른_세션의_고객_잠금은_기다린다(db_engine):
    """C14 판별 — PetPgRepository.lock_owner 의 FOR UPDATE 가 고객 행을 실제로 잠그는지 저장소 수준에서 본다.

    UpdatePetInteractor 를 거쳐서는 이걸 확인할 수 없다. 익명화가 pets 행도 고치므로, lock_owner 의
    잠금을 빼도 update 쪽은 pets 행의 암묵적 잠금에서 기다렸다가 같은 결과(404)가 나온다(변이로
    확인함) — 같은 결과가 다른 이유로도 나올 수 있어 판별력이 없다. 그래서 저장소 수준으로 내려가
    lock_owner 만 불러 고객 행을 쥐고, 같은 고객 행을 CustomerPgRepository.lock_active 로 다시
    잠그려는 세션이 기다리는지를 직접 본다. lock_owner 의 `.with_for_update(of=CustomerOrm)` 을
    지우면 이 테스트가 바로 실패한다(기다리지 않는다) — 판별력이 있다는 뜻이다.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (pet_id,) = await _family(factory)

    async with factory() as locking, factory() as relocking:
        locked_customer_id = await PetPgRepository(locking).lock_owner(SHOP, pet_id)
        assert locked_customer_id == customer_id

        relock = asyncio.create_task(CustomerPgRepository(relocking).lock_active(SHOP, customer_id))
        assert await _still_waiting(relock)

        await locking.commit()
        relocked = await relock
        assert relocked.id == customer_id
        await relocking.rollback()


async def test_마지막_두_마리를_동시에_지우면_하나는_LAST_PET_이다(db_engine):
    """C13 — 고객 행을 잠근 뒤 센다. 잠금이 없으면 둘 다 '두 마리'로 보고 지워 반려동물 없는 가족이 남는다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong, dubu) = await _family(factory, pet_names=("콩이", "두부"))

    async with factory() as first, factory() as second:
        _, pets, _, search = _repos(first)
        await DeletePetInteractor(pets, search, _ledger(first), events=NoEvents(), **_consent(first)).delete_pet(DeletePetCommand(ctx=SHOP, pet_id=kong))
        _, pets, _, search = _repos(second)
        late = asyncio.create_task(
            DeletePetInteractor(pets, search, _ledger(second), events=NoEvents(), **_consent(second)).delete_pet(DeletePetCommand(ctx=SHOP, pet_id=dubu))
        )
        assert await _still_waiting(late)

        await first.commit()
        with pytest.raises(LastPetError):
            await late
        await second.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM pets WHERE customer_id = :id", id=customer_id) == 1
