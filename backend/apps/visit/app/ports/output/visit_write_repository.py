from __future__ import annotations

from abc import abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.domain.entities.visit import Visit
from visit.domain.state.visit_state import StatusChange
from visit.domain.value_objects.new_visit import NewVisit


class VisitWriteRepository(VisitLookupRepository):
    """방문을 만들고 고치고 상태를 바꾼다. 찾기·잠금(`VisitLookupRepository`)을 포함한다.

    쓰는 유스케이스(등록·수정·옮기기·전이)만 받는다. 조회 유스케이스는 이 포트를 받지 않는다.
    """

    @abstractmethod
    async def create_many(self, ctx: ShopContext, visits: list[NewVisit]) -> list[Visit]:
        """한 번에 넣는다. 같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있으면
        VisitDuplicateError — 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""

    @abstractmethod
    async def update_details(
        self, ctx: ShopContext, visit_id: int, starts_at: datetime, pet_id: int | None,
        duration_minutes: int, menu_ids: tuple[int, ...], memo: str | None,
    ) -> Visit:
        """메뉴는 통째로 바꾼다. 중복 예약이 되면 VisitDuplicateError."""

    @abstractmethod
    async def reschedule(self, ctx: ShopContext, visit_ids: list[int], starts_at: datetime) -> list[Visit]:
        """여러 방문의 시작 시각을 한 번에 바꾼다. 중복 예약이 되면 VisitDuplicateError(전부 되돌린다)."""

    @abstractmethod
    async def apply_changes(
        self, ctx: ShopContext, changes: list[tuple[int, StatusChange]], member_id: int
    ) -> list[Visit]:
        """상태 칸을 통째로 바꾸고 바꾼 멤버를 찍는다. 되돌리기가 중복 예약이 되면 VisitDuplicateError(전부 되돌린다)."""

    @abstractmethod
    async def set_report_skipped(self, ctx: ShopContext, visit_id: int, at: datetime | None) -> None:
        """하루 마무리의 "알림장을 보내지 않음"(⑬) — at 이 None 이면 되돌린다. 방문 행을 잠근 뒤 부른다."""
