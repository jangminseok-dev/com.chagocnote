from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ParseVisitDraftCommand:
    """카톡 글 하나. 저장하지 않고 초안만 돌려준다 — 글은 로그·DB·오류 응답에 남기지 않는다(V9)."""

    ctx: ShopContext
    text: str


@dataclass(frozen=True)
class DraftPetView:
    pet_id: int
    name: str


@dataclass(frozen=True)
class DraftCandidateView:
    customer_id: int
    name: str
    phone_masked: str
    pets: list[DraftPetView]        # 무지개다리 제외
    matched_pet_ids: list[int]      # 글의 낱말과 이름이 같은 아이


@dataclass(frozen=True)
class DraftGuessView:
    """짐작함 — 사람이 확인해야 하는 칸."""

    date: bool
    time: bool
    who: bool
    menu: bool


@dataclass(frozen=True)
class VisitDraftView:
    date: date | None
    time: time | None
    customer_candidates: list[DraftCandidateView]   # 최대 5 가족
    pet_ids: list[int]                              # 후보가 하나일 때 그 후보의 matched_pet_ids
    menu_ids: list[int]                             # 메뉴표 순서
    guessed: DraftGuessView
