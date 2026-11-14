from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SourceDocument:
    """검색에 넣을 글 하나(⑨ 설계 3.2). 글을 가진 스포크가 만들어 search 에 내준다. 로그에 남기지 않는다."""

    kind: str                 # care_note · internal_note · visit_memo · pet_memo · condition_note · customer_memo
    source_id: int            # 그 kind 의 원본 행 ID — 방문 계열은 방문, pet_memo 는 반려동물, condition_note 는 지병 행, customer_memo 는 고객
    customer_id: int
    pet_id: int | None        # 보호자만의 방문·보호자 메모는 None
    visit_id: int | None      # 방문 계열만
    happened_on: date | None  # 방문 계열만 — 매장 시간대의 방문 날
    body: str                 # 앞뒤 공백을 뗀, 비어 있지 않은 글
