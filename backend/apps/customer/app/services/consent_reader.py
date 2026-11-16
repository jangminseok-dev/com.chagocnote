"""동의서 한 장을 지금의 사실로 읽는다(⑪ 설계 3.2·3.3). 발급·현장 서명·공개 읽기·제출이 함께 쓴다."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.entities.consent import ConsentPolicy, DocumentPet, PetConsentFacts
from customer.domain.entities.pet import Pet
from customer.domain.errors import CustomerInputError
from customer.domain.services.consent_document import build_document, doc_digest
from customer.app.services.consent_source import ConsentText, default_texts
from customer.domain.services.consent_text import PARTS
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ConsentDocument:
    customer_id: int
    pets: tuple[DocumentPet, ...]          # 다시 받을 토막이 남은 아이만
    texts: dict[str, ConsentText]          # 이 문서가 쓰는 토막만, 문서의 순서대로
    previous_consent_on: date | None       # 바뀐 토막만 받는 아이가 있으면 그 동의를 받은 날
    digest: str


def facts_of(pet: Pet, signed=()) -> PetConsentFacts:
    return PetConsentFacts(
        pet_id=pet.id, name=pet.name, birth_date=pet.birth_date, birth_year=pet.birth_year,
        # 보호자에게 보이는 이름이다 — 예약 앞의 확인할 것(care_facts)과 같은 규칙.
        condition_labels=tuple(c.custom_label or c.label for c in pet.conditions),
        consent_on=pet.grooming_consent_on, via_signature=pet.grooming_consent_signature_id is not None,
        signed=tuple(signed), passed_away=pet.passed_away,
    )


async def read_document(
    ctx: ShopContext, pet_ids: tuple[int, ...], on: date, policy: ConsentPolicy, *,
    pets: PetRepository, signatures: ConsentSignatureRepository, texts: dict[str, ConsentText] | None = None,
) -> ConsentDocument:
    """그 아이들의 동의서를 기준일(on — 오늘이거나 예약 날)로 조립한다. 없는 아이·익명화한 고객의 아이·다른 매장의 아이면 PetNotFoundError,
    한 가족이 아니면 CustomerInputError. 다시 받을 것이 없으면 pets 가 비어 있다.
    texts 는 토막별 지금 글(매장이 고친 글 포함)이다 — 주지 않으면 기본 글."""
    found = [await pets.get(ctx, pet_id) for pet_id in sorted(set(pet_ids))]
    if not found:
        raise CustomerInputError("아이를 하나 이상 골라 주세요.")
    owners = {pet.customer_id for pet in found}
    if len(owners) != 1:
        raise CustomerInputError("한 가족의 아이만 함께 보낼 수 있습니다.")
    since = {pet.id: pet.grooming_consent_signature_id for pet in found
             if pet.grooming_consent_on is not None and pet.grooming_consent_signature_id is not None}
    covers = await signatures.covers(ctx, since)
    doc = build_document([facts_of(pet, covers.get(pet.id, ())) for pet in found], on, policy)
    texts = texts or default_texts()
    used = [part for part in PARTS if any(part in pet.parts for pet in doc)]
    partial = [pet.grooming_consent_on for pet in found
               if any(d.pet_id == pet.id and not d.full for d in doc)]
    return ConsentDocument(
        customer_id=owners.pop(), pets=doc, texts={part: texts[part] for part in used},
        previous_consent_on=min(partial) if partial else None,
        digest=doc_digest(doc, {part: (texts[part].source, texts[part].version) for part in used}),
    )
