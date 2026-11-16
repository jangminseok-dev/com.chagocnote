from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.consent_orm import (
    ConsentSignatureConditionOrm,
    ConsentSignatureOrm,
    ConsentSignaturePartOrm,
    ConsentSignaturePetOrm,
)
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.domain.entities.consent import SignedCover
from customer.domain.entities.consent_form import (
    HeldConsent,
    HeldSignature,
    NewSignature,
    SignatureBrief,
    SignatureDetail,
    SignaturePetDetail,
    SignedPart,
)
from customer.domain.errors import SignatureNotFoundError
from customer.domain.services.consent_text import PARTS
from hub.app.dtos.shop_context import ShopContext


def _in_order(parts) -> list:
    return sorted(parts, key=lambda p: PARTS.index(p.part if hasattr(p, "part") else p))


class ConsentSignaturePgRepository(ConsentSignatureRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, ctx: ShopContext, signature: NewSignature) -> int:
        signature_id = (
            await self._session.execute(
                insert(ConsentSignatureOrm).values(
                    shop_id=ctx.shop_id, customer_id=signature.customer_id, form_id=signature.form_id,
                    channel=signature.channel, signer_name=signature.signer_name,
                    signature_png=signature.signature_png, signed_at=signature.signed_at,
                    by_member_id=signature.by_member_id, intake_answer_id=signature.intake_answer_id,
                ).returning(ConsentSignatureOrm.id)
            )
        ).scalar_one()
        for pet in signature.pets:
            signature_pet_id = (
                await self._session.execute(
                    insert(ConsentSignaturePetOrm).values(
                        signature_id=signature_id, pet_id=pet.pet_id, shown_pet_name=pet.shown_pet_name,
                    ).returning(ConsentSignaturePetOrm.id)
                )
            ).scalar_one()
            await self._session.execute(insert(ConsentSignaturePartOrm), [
                {"signature_pet_id": signature_pet_id, "part": p.part, "text_source": p.text_source,
                 "text_version": p.text_version}
                for p in pet.parts
            ])
            if pet.condition_labels:
                await self._session.execute(insert(ConsentSignatureConditionOrm), [
                    {"signature_pet_id": signature_pet_id, "position": position, "label": label}
                    for position, label in enumerate(pet.condition_labels)
                ])
        return signature_id

    async def covers(self, ctx: ShopContext, since: Mapping[int, int]) -> dict[int, tuple[SignedCover, ...]]:
        if not since:
            return {}
        rows = (
            await self._session.execute(
                select(ConsentSignaturePetOrm.id, ConsentSignaturePetOrm.pet_id, ConsentSignatureOrm.id)
                .join(ConsentSignatureOrm, ConsentSignatureOrm.id == ConsentSignaturePetOrm.signature_id)
                .where(ConsentSignatureOrm.shop_id == ctx.shop_id, ConsentSignaturePetOrm.pet_id.in_(since))
                .order_by(ConsentSignatureOrm.id, ConsentSignaturePetOrm.id)
            )
        ).all()
        # 받은 날을 찍은 서명보다 앞의 것은 지금의 동의가 아니다 — 세지 않는다.
        kept = [(sp_id, pet_id) for sp_id, pet_id, signature_id in rows if signature_id >= since[pet_id]]
        parts, labels = await self._children([sp_id for sp_id, _ in kept])
        found: dict[int, list[SignedCover]] = {}
        for sp_id, pet_id in kept:
            found.setdefault(pet_id, []).append(SignedCover(
                parts=frozenset(p.part for p in parts.get(sp_id, [])),
                condition_labels=frozenset(labels.get(sp_id, [])),
            ))
        return {pet_id: tuple(covers) for pet_id, covers in found.items()}

    async def list_for_pet(self, ctx: ShopContext, pet_id: int) -> list[SignatureBrief]:
        rows = (
            await self._session.execute(
                select(ConsentSignatureOrm, ConsentSignaturePetOrm.id)
                .join(ConsentSignaturePetOrm, ConsentSignaturePetOrm.signature_id == ConsentSignatureOrm.id)
                .where(ConsentSignatureOrm.shop_id == ctx.shop_id, ConsentSignaturePetOrm.pet_id == pet_id)
                .order_by(ConsentSignatureOrm.signed_at.desc(), ConsentSignatureOrm.id.desc())
            )
        ).all()
        parts, _ = await self._children([sp_id for _, sp_id in rows])
        return [
            SignatureBrief(
                signature_id=row.id, signed_at=row.signed_at, channel=row.channel, signer_name=row.signer_name,
                parts=tuple(p.part for p in parts.get(sp_id, [])),
            )
            for row, sp_id in rows
        ]

    async def get(self, ctx: ShopContext, signature_id: int) -> SignatureDetail:
        row = await self._row(ctx, signature_id)
        pets = (
            await self._session.execute(
                select(ConsentSignaturePetOrm).where(ConsentSignaturePetOrm.signature_id == signature_id)
                .order_by(ConsentSignaturePetOrm.id)
            )
        ).scalars().all()
        parts, labels = await self._children([pet.id for pet in pets])
        return SignatureDetail(
            signature_id=row.id, signed_at=row.signed_at, channel=row.channel, signer_name=row.signer_name,
            by_member_id=row.by_member_id,
            pets=tuple(
                SignaturePetDetail(
                    pet_id=pet.pet_id, shown_pet_name=pet.shown_pet_name,
                    condition_labels=tuple(labels.get(pet.id, [])), parts=tuple(parts.get(pet.id, [])),
                )
                for pet in pets
            ),
        )

    async def image(self, ctx: ShopContext, signature_id: int) -> bytes:
        return bytes((await self._row(ctx, signature_id)).signature_png)

    async def delete_for_customer(self, ctx: ShopContext, customer_id: int) -> int:
        result = await self._session.execute(
            delete(ConsentSignatureOrm).where(
                ConsentSignatureOrm.shop_id == ctx.shop_id, ConsentSignatureOrm.customer_id == customer_id)
        )
        return result.rowcount

    async def delete_for_pet(self, ctx: ShopContext, pet_id: int) -> int:
        owned = select(ConsentSignatureOrm.id).where(ConsentSignatureOrm.shop_id == ctx.shop_id)
        touched = (
            await self._session.execute(
                select(ConsentSignaturePetOrm.signature_id).where(
                    ConsentSignaturePetOrm.pet_id == pet_id, ConsentSignaturePetOrm.signature_id.in_(owned))
            )
        ).scalars().all()
        result = await self._session.execute(
            delete(ConsentSignaturePetOrm).where(
                ConsentSignaturePetOrm.pet_id == pet_id, ConsentSignaturePetOrm.signature_id.in_(owned))
        )
        if touched:
            left = select(ConsentSignaturePetOrm.signature_id)
            await self._session.execute(
                delete(ConsentSignatureOrm).where(
                    ConsentSignatureOrm.id.in_(touched), ConsentSignatureOrm.id.not_in(left))
            )
        return result.rowcount

    async def _row(self, ctx: ShopContext, signature_id: int) -> ConsentSignatureOrm:
        row = (
            await self._session.execute(
                select(ConsentSignatureOrm).where(
                    ConsentSignatureOrm.id == signature_id, ConsentSignatureOrm.shop_id == ctx.shop_id)
            )
        ).scalar_one_or_none()
        if row is None:
            raise SignatureNotFoundError("서명을 찾을 수 없습니다.")
        return row

    async def _children(self, signature_pet_ids: list[int]) -> tuple[dict[int, list[SignedPart]], dict[int, list[str]]]:
        if not signature_pet_ids:
            return {}, {}
        parts: dict[int, list[SignedPart]] = {}
        for row in (await self._session.execute(
            select(ConsentSignaturePartOrm).where(ConsentSignaturePartOrm.signature_pet_id.in_(signature_pet_ids))
        )).scalars():
            parts.setdefault(row.signature_pet_id, []).append(
                SignedPart(part=row.part, text_source=row.text_source, text_version=row.text_version))
        labels: dict[int, list[str]] = {}
        for sp_id, label in await self._session.execute(
            select(ConsentSignatureConditionOrm.signature_pet_id, ConsentSignatureConditionOrm.label)
            .where(ConsentSignatureConditionOrm.signature_pet_id.in_(signature_pet_ids))
            .order_by(ConsentSignatureConditionOrm.signature_pet_id, ConsentSignatureConditionOrm.position)
        ):
            labels.setdefault(sp_id, []).append(label)
        return {sp_id: _in_order(found) for sp_id, found in parts.items()}, labels

    async def adopt_held(
        self, ctx: ShopContext, answer_id: int, *, customer_id: int, pet_id: int,
    ) -> HeldSignature | None:
        # 고객을 채우는 것과 답에서 떼는 것을 한 번에 한다 — 고객도 답도 없는 서명은 없다(CHECK).
        row = (
            await self._session.execute(
                update(ConsentSignatureOrm)
                .where(ConsentSignatureOrm.shop_id == ctx.shop_id, ConsentSignatureOrm.intake_answer_id == answer_id,
                       ConsentSignatureOrm.customer_id.is_(None))
                .values(customer_id=customer_id, intake_answer_id=None)
                .returning(ConsentSignatureOrm.id, ConsentSignatureOrm.signed_at, ConsentSignatureOrm.by_member_id)
            )
        ).first()
        if row is None:
            return None
        await self._session.execute(
            update(ConsentSignaturePetOrm).where(ConsentSignaturePetOrm.signature_id == row.id).values(pet_id=pet_id))
        return HeldSignature(signature_id=row.id, signed_at=row.signed_at, by_member_id=row.by_member_id)

    async def held_for(self, ctx: ShopContext, answer_ids: list[int]) -> dict[int, HeldConsent]:
        if not answer_ids:
            return {}
        rows = (
            await self._session.execute(
                select(ConsentSignatureOrm.intake_answer_id, ConsentSignatureOrm.signed_at, ConsentSignaturePetOrm.id)
                .join(ConsentSignaturePetOrm, ConsentSignaturePetOrm.signature_id == ConsentSignatureOrm.id)
                .where(ConsentSignatureOrm.shop_id == ctx.shop_id,
                       ConsentSignatureOrm.intake_answer_id.in_(answer_ids))
            )
        ).all()
        parts, _ = await self._children([sp_id for _, _, sp_id in rows])
        return {
            answer_id: HeldConsent(signed_at=signed_at, parts=tuple(p.part for p in _in_order(parts.get(sp_id, []))))
            for answer_id, signed_at, sp_id in rows
        }

