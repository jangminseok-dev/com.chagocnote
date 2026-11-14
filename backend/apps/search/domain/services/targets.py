"""다시 색인하는 대상(scope, ref_id)에 어떤 문서가 드는가 — 한 곳에서 정한다.

    visit     그 방문의 케어 노트·내부 메모·예약 메모 (source_id 가 방문)
    pet       그 아이의 특이사항(source_id 가 아이)과 지병들(pet_id 가 아이 — 지병은 원본 ID 가 지병 행이다)
    customer  그 보호자의 메모 (source_id 가 고객)
"""
from __future__ import annotations

from dataclasses import dataclass

from search.domain.entities.search_document import VISIT_KINDS, SearchDocument


@dataclass(frozen=True)
class TargetFilter:
    by_source: tuple[str, ...]   # source_id = ref_id 로 묶이는 kind
    by_pet: tuple[str, ...]      # pet_id = ref_id 로 묶이는 kind


_FILTERS = {
    "visit": TargetFilter(by_source=VISIT_KINDS, by_pet=()),
    "pet": TargetFilter(by_source=("pet_memo",), by_pet=("condition_note",)),
    "customer": TargetFilter(by_source=("customer_memo",), by_pet=()),
}


def target_filter(scope: str) -> TargetFilter:
    if scope not in _FILTERS:
        raise ValueError("모르는 색인 대상입니다.")
    return _FILTERS[scope]


def belongs(document: SearchDocument, scope: str, ref_id: int) -> bool:
    rule = target_filter(scope)
    return (document.kind in rule.by_source and document.source_id == ref_id) or (
        document.kind in rule.by_pet and document.pet_id == ref_id
    )
