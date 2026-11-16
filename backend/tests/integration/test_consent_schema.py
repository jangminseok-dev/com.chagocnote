"""서류 요청과 서명의 표·저장소 — 실제 PG 로 확인한다(⑪-A)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.link_token import new_public_id
from customer.adapter.outbound.pg.consent_form_pg_repository import ConsentFormPgRepository
from customer.adapter.outbound.pg.consent_signature_pg_repository import ConsentSignaturePgRepository
from customer.domain.entities.consent import SignedCover
from customer.domain.entities.consent_form import NewSignature, NewSignaturePet, SignedPart
from customer.domain.errors import FormNotFoundError, SignatureNotFoundError
from hub.app.dtos.shop_context import ShopContext
from tests.integration.test_visit_checks_wiring import HEART, _family, _pet, _shop

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 16, 3, 0, tzinfo=timezone.utc)      # 서울 2026-11-16 12:00
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


def _ctx(shop_id: int, member_id: int = 7) -> ShopContext:
    return ShopContext(shop_id=shop_id, member_id=member_id, role="owner", permissions=frozenset())


def _signature(customer_id, pet_id, *parts, labels=(), signed_at=NOW, form_id=None, png=PNG) -> NewSignature:
    return NewSignature(
        customer_id=customer_id, form_id=form_id, channel="link" if form_id else "in_shop",
        signer_name="김민지", signature_png=png, signed_at=signed_at, by_member_id=7,
        pets=(NewSignaturePet(pet_id=pet_id, shown_pet_name="콩이",
                              parts=tuple(SignedPart(p, "default", 1) for p in parts),
                              condition_labels=tuple(labels)),),
    )


@pytest.fixture
async def family(wired):
    shop_id, headers, operator = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(conditions=[HEART]))
    return wired, shop_id, customer_id, pet_id, operator


def _session(wired):
    return async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)()


async def test_마이그레이션_뒤에_표와_제약이_있다(db_session):
    tables = set((await db_session.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))).scalars())
    assert {"customer_forms", "customer_form_pets", "consent_signatures", "consent_signature_pets",
            "consent_signature_parts", "consent_signature_conditions"} <= tables
    checks = set((await db_session.execute(text("SELECT conname FROM pg_constraint"))).scalars())
    assert {"ck_customer_forms_kind", "ck_consent_signatures_channel", "ck_consent_signatures_png_size",
            "ck_consent_signatures_link_has_form", "ck_pets_grooming_consent_signature_needs_day",
            "uq_customer_forms_public_id", "uq_consent_signatures_form_id"} <= checks


async def test_요청을_만들고_읽고_끊는다(family):
    wired, shop_id, customer_id, pet_id, _ = family
    async with _session(wired) as session:
        forms = ConsentFormPgRepository(session)
        form = await forms.create(_ctx(shop_id), customer_id, (pet_id,), new_public_id(), NOW + timedelta(days=14))
        assert (form.customer_id, form.pet_ids, form.created_by_member_id) == (customer_id, (pet_id,), 7)
        assert form.is_live(NOW) and not form.is_live(NOW + timedelta(days=14))
        assert [f.id for f in await forms.live_for_customer(_ctx(shop_id), customer_id, NOW)] == [form.id]
        assert (await forms.find_public(form.public_id)).id == form.id
        assert await forms.find_public(new_public_id()) is None
        assert set(await forms.sent_on(_ctx(shop_id), (pet_id, 999), NOW)) == {pet_id}

        await forms.revoke(_ctx(shop_id), form.id, NOW)
        assert (await forms.get(_ctx(shop_id), form.id)).revoked_at == NOW
        assert await forms.list_live(_ctx(shop_id), NOW) == []
        assert await forms.sent_on(_ctx(shop_id), (pet_id,), NOW) == {}


async def test_기간이_지났거나_낸_요청은_살아_있는_것에_없다(family):
    wired, shop_id, customer_id, pet_id, _ = family
    async with _session(wired) as session:
        forms = ConsentFormPgRepository(session)
        old = await forms.create(_ctx(shop_id), customer_id, (pet_id,), new_public_id(), NOW - timedelta(seconds=1))
        sent = await forms.create(_ctx(shop_id), customer_id, (pet_id,), new_public_id(), NOW + timedelta(days=1))
        await forms.mark_submitted(sent.id, NOW)
        assert await forms.list_live(_ctx(shop_id), NOW) == []
        assert old.is_closed(NOW) and not (await forms.get(_ctx(shop_id), sent.id)).is_closed(NOW)


async def test_다른_매장의_요청과_서명은_못_찾고_못_끊는다(family):
    wired, shop_id, customer_id, pet_id, operator = family
    other_shop, _, _ = await _shop(wired, name="다른 매장", owner="다른 사장", operator=operator)
    async with _session(wired) as session:
        forms, signatures = ConsentFormPgRepository(session), ConsentSignaturePgRepository(session)
        form = await forms.create(_ctx(shop_id), customer_id, (pet_id,), new_public_id(), NOW + timedelta(days=14))
        signature_id = await signatures.add(_ctx(shop_id), _signature(customer_id, pet_id, "basic"))
        with pytest.raises(FormNotFoundError):
            await forms.get(_ctx(other_shop), form.id)
        await forms.revoke(_ctx(other_shop), form.id, NOW)
        await forms.set_pets(_ctx(other_shop), form.id, ())
        assert (await forms.get(_ctx(shop_id), form.id)).revoked_at is None
        assert (await forms.get(_ctx(shop_id), form.id)).pet_ids == (pet_id,)
        with pytest.raises(SignatureNotFoundError):
            await signatures.get(_ctx(other_shop), signature_id)
        with pytest.raises(SignatureNotFoundError):
            await signatures.image(_ctx(other_shop), signature_id)
        assert await signatures.list_for_pet(_ctx(other_shop), pet_id) == []
        assert await signatures.delete_for_customer(_ctx(other_shop), customer_id) == 0
        assert await signatures.delete_for_pet(_ctx(other_shop), pet_id) == 0
        assert await signatures.covers(_ctx(other_shop), {pet_id: signature_id}) == {}


async def test_서명을_쓰고_그대로_읽는다(family):
    wired, shop_id, customer_id, pet_id, _ = family
    async with _session(wired) as session:
        signatures = ConsentSignaturePgRepository(session)
        signature_id = await signatures.add(
            _ctx(shop_id), _signature(customer_id, pet_id, "condition", "basic", labels=("심장 질환", "피부")))
        detail = await signatures.get(_ctx(shop_id), signature_id)
        assert (detail.channel, detail.signer_name, detail.by_member_id) == ("in_shop", "김민지", 7)
        (pet,) = detail.pets
        assert (pet.pet_id, pet.shown_pet_name, pet.condition_labels) == (pet_id, "콩이", ("심장 질환", "피부"))
        assert [p.part for p in pet.parts] == ["basic", "condition"]            # 문서의 순서
        assert await signatures.image(_ctx(shop_id), signature_id) == PNG
        (brief,) = await signatures.list_for_pet(_ctx(shop_id), pet_id)
        assert (brief.signature_id, brief.parts) == (signature_id, ("basic", "condition"))


async def test_covers_는_받은_날을_찍은_서명부터_센다(family):
    wired, shop_id, customer_id, pet_id, _ = family
    async with _session(wired) as session:
        signatures = ConsentSignaturePgRepository(session)
        await signatures.add(_ctx(shop_id), _signature(customer_id, pet_id, "basic", "senior"))     # 지금의 동의 앞
        current = await signatures.add(_ctx(shop_id), _signature(
            customer_id, pet_id, "basic", "condition", labels=("심장 질환",)))
        later = await signatures.add(_ctx(shop_id), _signature(customer_id, pet_id, "condition", labels=("피부",)))
        covers = await signatures.covers(_ctx(shop_id), {pet_id: current})
        assert later > current
        assert covers == {pet_id: (
            SignedCover(frozenset({"basic", "condition"}), frozenset({"심장 질환"})),
            SignedCover(frozenset({"condition"}), frozenset({"피부"})),
        )}


async def test_아이의_서명을_지우면_아이가_남지_않은_서명도_지워진다(family):
    wired, shop_id, customer_id, pet_id, _ = family
    async with _session(wired) as session:
        signatures = ConsentSignaturePgRepository(session)
        await signatures.add(_ctx(shop_id), _signature(customer_id, pet_id, "basic", labels=("심장 질환",)))
        assert await signatures.delete_for_pet(_ctx(shop_id), pet_id) == 1
        for table in ("consent_signatures", "consent_signature_pets", "consent_signature_parts",
                      "consent_signature_conditions"):
            assert (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one() == 0, table


async def test_고객의_서명을_지우면_아래_줄까지_지워진다(family):
    wired, shop_id, customer_id, pet_id, _ = family
    async with _session(wired) as session:
        signatures = ConsentSignaturePgRepository(session)
        await signatures.add(_ctx(shop_id), _signature(customer_id, pet_id, "basic", labels=("심장 질환",)))
        assert await signatures.delete_for_customer(_ctx(shop_id), customer_id) == 1
        for table in ("consent_signatures", "consent_signature_pets", "consent_signature_parts",
                      "consent_signature_conditions"):
            assert (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one() == 0, table


async def test_서명_그림이_65537_바이트면_DB_가_거절한다(family):
    wired, shop_id, customer_id, pet_id, _ = family
    async with _session(wired) as session:
        with pytest.raises(IntegrityError):
            await ConsentSignaturePgRepository(session).add(
                _ctx(shop_id), _signature(customer_id, pet_id, "basic", png=b"\x00" * 65537))


async def test_받은_날_없이_서명_ID_만_있는_동의는_DB_가_거절한다(family):
    wired, _, _, pet_id, _ = family
    async with _session(wired) as session:
        with pytest.raises(IntegrityError):
            await session.execute(text(
                "UPDATE pets SET grooming_consent_signature_id = 1 WHERE id = :id"), {"id": pet_id})
