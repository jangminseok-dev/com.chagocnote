from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.family_brief import FamilyBriefs
from hub.app.dtos.shop_context import ShopContext


class CustomerDirectoryPort(ABC):
    """구현: customer. 사용: visit (예약 등록·수정·상태 전이, 목록의 이름 표시, 최근 방문순)."""

    @abstractmethod
    async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
        """고객 행을 FOR UPDATE 로 잠그고 확인한다: 살아 있는 이 매장의 고객인가, 반려동물이 모두 그 보호자의
        아이이고 무지개다리가 아닌가. 통과하지 못하면 구현 쪽 도메인 오류(CUSTOMER_NOT_FOUND·PET_NOT_FOUND·
        PET_PASSED_AWAY)를 던진다.

        잠금은 부르는 쪽 트랜잭션이 끝날 때 풀린다. 방문을 쓰는 유스케이스는 방문 행을 잠그기 **전에** 부른다
        (잠금 순서: 고객 행 → 방문 행). 익명화·무지개다리·반려동물 삭제와 겹치지 않게 하려는 것이다.
        """

    @abstractmethod
    async def briefs(
        self, ctx: ShopContext, customer_ids: list[int], pet_ids: list[int]
    ) -> FamilyBriefs:
        """보여 줄 요약. 익명화한 고객과 그 반려동물도 틀은 돌려준다(이름은 None)."""

    @abstractmethod
    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
        """고객 목록 '최근 방문순'의 키를 바꾼다. 원본(visits)에서 다시 계산한 값을 같은 트랜잭션에서 넘긴다."""
