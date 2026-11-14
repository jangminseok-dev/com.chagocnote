from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class SearchRecordsQuery:
    ctx: ShopContext
    q: str                    # 받은 그대로 — 인터랙터가 다듬고 길이를 본다
    pet_id: int | None        # 주면 그 아이(와 그 아이 보호자의 메모) 안에서만 찾는다


@dataclass(frozen=True)
class SearchItemView:
    kind: str
    customer_id: int
    owner_name: str           # 늘 있다 — 아이가 없는 줄은 보호자 이름을 보인다
    pet_id: int | None        # 보호자 메모·보호자만의 방문은 None
    pet_name: str | None
    photo: str | None         # 아이의 프로필 사진(가장 최근 대표) 썸네일 주소
    visit_id: int | None      # 있으면 방문 상세로 간다
    open_pet_id: int | None   # 방문이 없는 줄을 눌렀을 때 열 반려동물
    date: date | None         # 방문 날
    snippet: str


@dataclass(frozen=True)
class SearchResultView:
    items: list[SearchItemView]
    semantic: bool            # 뜻 검색이 함께 됐는가(임베딩을 받았는가) — 진단용
