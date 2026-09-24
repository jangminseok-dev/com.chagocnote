from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from customer.app.dtos.customer_search_dto import SearchPage, SearchRequest
from customer.domain.services.search_terms import SearchWord
from hub.app.dtos.shop_context import ShopContext


class CustomerSearchPort(ABC):
    """가족 단위 검색. 지금 구현은 PostgreSQL(pg_trgm)이고, 전용 검색 엔진으로 바꿀 때 어댑터만 교체한다.

    검색 결과는 고객 ID 뿐이다. 화면에 보여 줄 보호자·반려동물 정보는 원본 표에서 읽는다.
    """

    @abstractmethod
    async def rebuild_search_entry(self, ctx: ShopContext, customer_id: int) -> None:
        """그 가족의 검색 줄을 원본에서 다시 만든다. 고객이 익명화됐거나 없으면 줄을 지운다.

        가족(고객·반려동물·질병)을 바꾸는 모든 유스케이스가 같은 트랜잭션 안에서 부른다.
        """

    @abstractmethod
    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
        """'최근 방문순'의 키를 바꾼다. 검색 줄이 없으면(익명화한 고객) 아무것도 하지 않는다.

        원본은 visits 다 — visit 스포크가 허브 포트(CustomerDirectoryPort)로 알려 준다.
        """

    @abstractmethod
    async def search(self, ctx: ShopContext, request: SearchRequest) -> SearchPage:
        """커서가 올바르지 않으면 CustomerInputError."""

    @abstractmethod
    async def count_pets(
        self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool
    ) -> int:
        """검색에 걸린 가족들의 반려동물 수(목록 제목의 'N마리'). 쪽과 상관없이 전체를 센다."""

    @abstractmethod
    async def match_any(self, ctx: ShopContext, words: tuple[SearchWord, ...], limit: int) -> list[int]:
        """낱말 **하나라도** 걸리는(OR) 이 매장의 가족(검색 줄이 있는 = 익명화하지 않은)의 고객 ID.

        고객 ID 오름차순으로 limit 개까지. 무지개다리만 남은 가족도 든다(보호자만의 예약이 있다).
        카톡 초안의 후보 찾기가 쓴다 — 순위는 부르는 쪽이 이름을 읽어 매긴다.
        """
