"""서명이 고객 행을 먼저 잠그는지 — 다른 트랜잭션이 고객 행을 쥔 채 지병을 더하면 서명이 거절되는 것으로 확인한다(⑪-A).

기다리는지만 보아서는 모자라다 — 잠금이 없어도 서명 행의 외래 키 검사가 같은 고객 행에서 기다린다. 다른 것은 **언제** 읽느냐다.

잠금 순서는 고객 행 → 서류 요청 행이다. 익명화·지병 수정·발급이 같은 고객 행을 잡으므로, 서명이 그 뒤에 서야
"익명화한 고객에게 서명이 남는다"·"읽은 뒤 바뀐 지병에 서명한다"가 생기지 않는다.
"""
import asyncio
import base64
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config import REPORT_LINK_KEY
from customer.adapter.outbound.pg.consent_form_pg_repository import ConsentFormPgRepository
from customer.adapter.outbound.pg.consent_signature_pg_repository import ConsentSignaturePgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.dtos.public_form_dto import SubmitPublicConsentCommand
from customer.app.dtos.sign_consent_in_shop_dto import SignConsentInShopCommand
from customer.app.use_cases.sign_consent_in_shop_interactor import SignConsentInShopInteractor
from customer.app.use_cases.submit_public_consent_interactor import SubmitPublicConsentInteractor
from customer.app.services.consent_source import ConsentSource
from customer.domain.errors import ConsentDocumentChangedError
from customer.domain.services.pet_age import seoul_today
from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from tests.integration.test_consent_wiring import PNG_B64, SENIOR_YEAR, count, document, send
from tests.integration.test_visit_checks_wiring import _family, _pet, _shop

pytestmark = pytest.mark.integration

BLOCKED = 0.5   # 이만큼 기다려도 끝나지 않으면 잠금에서 기다리는 것으로 본다
PNG = base64.b64decode(PNG_B64)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _Shops:
    async def public_profile(self, shop_id):
        return ShopProfile(shop_id=shop_id, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)


class _Limiter:
    async def allow(self, client): return True
    async def note_miss(self, client): return None
    async def missed_too_much(self, client): return False
    async def allow_write(self, client): return True


async def _still_waiting(task) -> bool:
    done, _ = await asyncio.wait({task}, timeout=BLOCKED)
    return not done


async def _world(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    token = (await send(wired, shop_id, headers, pet_id)).json()["url"].rsplit("/", 1)[1]
    digest = (await document(wired, shop_id, headers, pet_id)).json()["doc_digest"]
    ctx = ShopContext(shop_id=shop_id, member_id=1, role="owner", permissions=frozenset())
    return ctx, customer_id, pet_id, token, digest, async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)


async def _add_condition(session, pet_id: int) -> None:
    """고객 행을 쥔 트랜잭션이 그 사이 지병을 하나 더한다 — 보호자가 읽은 문서가 낡는다."""
    await session.execute(text(
        "INSERT INTO pet_conditions (pet_id, type_code) VALUES (:pet_id, 'allergy')"), {"pet_id": pet_id})
    await session.execute(text("UPDATE pets SET no_known_conditions = false WHERE id = :pet_id"), {"pet_id": pet_id})


async def test_현장_서명은_고객_행을_기다린_뒤에_문서를_읽는다(wired):
    """잠금 없이 문서를 먼저 읽으면, 기다리는 사이 더해진 지병을 못 본 채 옛 지문으로 서명이 저장된다."""
    ctx, customer_id, pet_id, _, digest, factory = await _world(wired)

    async with factory() as holder, factory() as signing:
        await CustomerPgRepository(holder).lock_active(ctx, customer_id)
        await _add_condition(holder, pet_id)
        use_case = SignConsentInShopInteractor(
            PetPgRepository(signing), ConsentSignaturePgRepository(signing), ConsentFormPgRepository(signing),
            seoul_today, _now, ConsentSource())
        task = asyncio.create_task(use_case.sign_consent_in_shop(SignConsentInShopCommand(
            ctx=ctx, pet_ids=(pet_id,), doc_digest=digest, signer_name="김민지", signature_png=PNG)))

        assert await _still_waiting(task)
        await holder.commit()
        with pytest.raises(ConsentDocumentChangedError):
            await task
        await signing.rollback()

    assert await count(wired, "consent_signatures") == 0
    assert await count(wired, "pets", "grooming_consent_on IS NOT NULL") == 0


async def test_링크_서명은_고객_행을_기다린_뒤에_문서를_읽는다(wired):
    ctx, customer_id, pet_id, token, digest, factory = await _world(wired)

    async with factory() as holder, factory() as signing:
        await CustomerPgRepository(holder).lock_active(ctx, customer_id)
        await _add_condition(holder, pet_id)
        use_case = SubmitPublicConsentInteractor(
            ConsentFormPgRepository(signing), CustomerPgRepository(signing), PetPgRepository(signing),
            ConsentSignaturePgRepository(signing), _Shops(), _Limiter(), _now, ConsentSource(), REPORT_LINK_KEY)
        task = asyncio.create_task(use_case.submit_public_consent(SubmitPublicConsentCommand(
            token=token, client="203.0.113.7", doc_digest=digest, signer_name="김민지", signature_png=PNG)))

        assert await _still_waiting(task)
        await holder.commit()
        with pytest.raises(ConsentDocumentChangedError):
            await task
        await signing.rollback()

    assert await count(wired, "consent_signatures") == 0
    assert await count(wired, "customer_forms", "submitted_at IS NOT NULL") == 0
