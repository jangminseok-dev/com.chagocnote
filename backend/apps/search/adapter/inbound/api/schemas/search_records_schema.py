from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from search.app.dtos.search_records_dto import SearchItemView, SearchResultView


class SearchOwnerSchema(BaseModel):
    customer_id: int
    name: str


class SearchPetSchema(BaseModel):
    pet_id: int
    name: str
    photo: str | None   # 프로필 사진(가장 최근 대표) 썸네일 주소


class SearchItemSchema(BaseModel):
    """결과 한 줄 — 칸을 하나하나 적는다. 글 전체가 아니라 걸린 토막(snippet)만 싣는다."""

    kind: str                     # care_note · internal_note · visit_memo · pet_memo · condition_note · customer_memo
    owner: SearchOwnerSchema      # 늘 온다 — 아이가 없는 줄은 보호자 이름을 보인다
    pet: SearchPetSchema | None   # 보호자 메모·보호자만의 방문은 null
    visit_id: int | None          # 있으면 방문 상세로 간다
    open_pet_id: int | None       # 방문이 없는 줄을 눌렀을 때 열 반려동물
    date: date | None             # 방문 날(매장 시간대)
    snippet: str

    @classmethod
    def of(cls, view: SearchItemView) -> SearchItemSchema:
        pet = None
        if view.pet_id is not None and view.pet_name is not None:
            pet = SearchPetSchema(pet_id=view.pet_id, name=view.pet_name, photo=view.photo)
        return cls(
            kind=view.kind, owner=SearchOwnerSchema(customer_id=view.customer_id, name=view.owner_name), pet=pet,
            visit_id=view.visit_id, open_pet_id=view.open_pet_id, date=view.date, snippet=view.snippet,
        )


class SearchResultSchema(BaseModel):
    items: list[SearchItemSchema]
    semantic: bool   # 뜻 검색이 함께 됐는가. 화면은 이것으로 아무것도 그리지 않는다(진단용)

    @classmethod
    def of(cls, view: SearchResultView) -> SearchResultSchema:
        return cls(items=[SearchItemSchema.of(item) for item in view.items], semantic=view.semantic)
