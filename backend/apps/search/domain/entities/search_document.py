from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# 방문에 딸린 글 — 한 방문의 셋이 함께 걸리면 검색 결과에서 하나로 접는다.
VISIT_KINDS = ("care_note", "internal_note", "visit_memo")
KINDS = VISIT_KINDS + ("pet_memo", "condition_note", "customer_memo")
# 다시 색인하는 단위(허브의 SEARCH_SCOPES 와 같은 값).
SCOPES = ("visit", "pet", "customer")


@dataclass(frozen=True)
class SearchDocument:
    """검색되는 글 하나의 사본. 원본은 visit·customer 의 것이고 언제든 다시 만들 수 있다."""

    kind: str
    source_id: int                 # 그 kind 의 원본 행 ID — (매장, kind, source_id) 로 유일하다
    customer_id: int
    pet_id: int | None
    visit_id: int | None
    happened_on: date | None
    body: str
    embedding: tuple[float, ...] | None = None   # 아직 임베딩 전이거나 모델이 죽어 있었으면 None
    model: str | None = None                     # 벡터를 만든 모델 이름


@dataclass(frozen=True)
class ReindexJob:
    """다시 색인할 대상 하나. (매장, scope, ref_id) 로 유일하다."""

    id: int
    shop_id: int
    scope: str
    ref_id: int
    generation: int      # 같은 대상이 다시 바뀔 때마다 오른다 — 집은 뒤에 올랐으면 줄을 지우지 않는다
    attempts: int
