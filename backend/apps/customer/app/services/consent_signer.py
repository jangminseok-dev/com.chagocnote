"""서명 한 번을 받는다(⑪ 설계 3.3). 링크 서명과 현장 서명이 함께 쓴다."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_forms import drop_pets
from customer.app.services.consent_reader import read_document
from customer.domain.entities.consent import ConsentPolicy
from customer.domain.entities.consent_form import NewSignature, NewSignaturePet, SignedPart
from customer.domain.errors import ConsentDocumentChangedError, ConsentUpToDateError, CustomerInputError
from customer.domain.services.consent_document import base_date
from customer.domain.services.signature_image import check_png
from hub.app.dtos.shop_context import ShopContext

SIGNER_NAME_MAX = 50


@dataclass(frozen=True)
class SigningInput:
    pet_ids: tuple[int, ...]
    doc_digest: str            # 보호자가 읽은 문서의 지문
    signer_name: str
    signature_png: bytes
    channel: str               # link | in_shop
    form_id: int | None        # 링크 서명이면 그 요청
    by_member_id: int          # 보낸(또는 현장에서 받은) 멤버
    for_date: date | None = None   # 문서를 조립한 기준일(예약 날). 없으면 오늘


async def sign(
    ctx: ShopContext, entry: SigningInput, now: datetime, today: date, policy: ConsentPolicy, *,
    pets: PetRepository, signatures: ConsentSignatureRepository, forms: ConsentFormRepository,
) -> int:
    """서명을 쓰고 서명 ID 를 돌려준다. **고객 행을 이미 쥔 안에서** 부른다.

    사실을 다시 읽어 지문이 다르면 받지 않는다 — 읽은 뒤 지병이 더해졌거나 이름·글이 바뀌었다.
    문서는 기준일(예약 날이 있으면 그날)로 조립한다. 전체 서명인 아이는 받은 날을 **오늘**로 찍고, 바뀐 토막만 받은 아이는 받은 날을 두고 덮는 것만 는다.
    """
    name = entry.signer_name.strip()
    if not 1 <= len(name) <= SIGNER_NAME_MAX:
        raise CustomerInputError("이름은 1자에서 50자 사이로 적어 주세요.")
    check_png(entry.signature_png)
    doc = await read_document(
        ctx, entry.pet_ids, base_date(today, entry.for_date, policy), policy, pets=pets, signatures=signatures)
    if not doc.pets:
        raise ConsentUpToDateError("이미 받은 동의입니다.")
    if doc.digest != entry.doc_digest:
        raise ConsentDocumentChangedError("동의서의 내용이 바뀌었습니다. 다시 읽어 주세요.")
    signature_id = await signatures.add(ctx, NewSignature(
        customer_id=doc.customer_id, form_id=entry.form_id, channel=entry.channel, signer_name=name,
        signature_png=entry.signature_png, signed_at=now, by_member_id=entry.by_member_id,
        pets=tuple(
            NewSignaturePet(
                pet_id=pet.pet_id, shown_pet_name=pet.name, condition_labels=pet.condition_labels,
                parts=tuple(SignedPart(part, doc.texts[part].source, doc.texts[part].version) for part in pet.parts),
            )
            for pet in doc.pets
        ),
    ))
    for pet in doc.pets:
        if pet.full:
            await pets.set_grooming_consent(ctx, pet.pet_id, today, entry.by_member_id, signature_id)
    # 이번에 서명한 아이는 다른 살아 있는 링크에서 덜어 낸다 — 같은 것을 두 번 서명받지 않는다.
    await drop_pets(ctx, doc.customer_id, [pet.pet_id for pet in doc.pets], now, forms)
    return signature_id
