"""보호자·반려동물에서 기록 검색에 넣을 글을 고른다(⑨ 설계 3.2). 주의 고객 사유는 넣지 않는다. 글을 로그에 남기지 않는다."""
from __future__ import annotations

from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet
from hub.app.dtos.search_source import SourceDocument


def condition_body(label: str, note: str | None) -> str:
    """지병 하나의 글 — 이름과 메모. 메모가 없으면 이름만이다(지병 이름으로 찾을 수 있게)."""
    note = (note or "").strip()
    return f"{label} — {note}" if note else label


def pet_documents(pet: Pet) -> list[SourceDocument]:
    """특이사항 하나와 지병마다 하나. 무지개다리를 건넌 아이의 글도 찾아진다."""
    documents = []
    if pet.memo and pet.memo.strip():
        documents.append(SourceDocument(
            kind="pet_memo", source_id=pet.id, customer_id=pet.customer_id, pet_id=pet.id, visit_id=None,
            happened_on=None, body=pet.memo.strip()))
    for condition in pet.conditions:
        documents.append(SourceDocument(
            kind="condition_note", source_id=condition.condition_id, customer_id=pet.customer_id, pet_id=pet.id,
            visit_id=None, happened_on=None,
            body=condition_body(condition.custom_label or condition.label, condition.note)))
    return documents


def customer_documents(customer: Customer) -> list[SourceDocument]:
    if not (customer.memo and customer.memo.strip()):
        return []
    return [SourceDocument(
        kind="customer_memo", source_id=customer.id, customer_id=customer.id, pet_id=None, visit_id=None,
        happened_on=None, body=customer.memo.strip())]
