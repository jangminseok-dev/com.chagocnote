from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from customer.domain.services.search_terms import SearchWord

SortKey = Literal["recent", "name", "last_visit"]
PAGE_SIZE = 30


@dataclass(frozen=True)
class SearchRequest:
    words: tuple[SearchWord, ...]
    sort: SortKey
    include_passed: bool
    cursor: str | None
    limit: int = PAGE_SIZE


@dataclass(frozen=True)
class SearchPage:
    """찾은 가족(고객 ID)을 정렬 순서대로. 다음 쪽이 없으면 next_cursor 는 None."""

    customer_ids: list[int]
    next_cursor: str | None
