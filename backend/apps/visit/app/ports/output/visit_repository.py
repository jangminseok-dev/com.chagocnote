from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit
from visit.domain.value_objects.new_visit import NewVisit


class VisitRepository(ABC):
    """방문. 모든 메서드가 ShopContext 의 매장으로 거른다."""

    @abstractmethod
    async def create_many(self, ctx: ShopContext, visits: list[NewVisit]) -> list[Visit]:
        """한 번에 넣는다. 같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있으면
        VisitDuplicateError — 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""

    @abstractmethod
    async def get(self, ctx: ShopContext, visit_id: int) -> Visit:
        """없거나 다른 매장이면 VisitNotFoundError."""

    @abstractmethod
    async def get_many(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
        """이 매장의 것만 돌려준다 — 모자라면 부르는 쪽이 없는 것으로 본다."""

    @abstractmethod
    async def lock(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
        """방문 행을 ID 오름차순으로 FOR UPDATE 잠그고 다시 읽는다. 고객 행을 잠근 **뒤에** 부른다(설계 4.2).
        이 매장의 것만 돌려준다 — 모자라면 부르는 쪽이 없는 것으로 본다."""

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
    async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
        """같은 가족 묶음(같은 보호자 + 같은 시작 시각)의 방문 — 상태와 상관없이."""

    @abstractmethod
    async def last_completed_before(
        self, ctx: ShopContext, customer_id: int, pet_id: int | None, before: datetime
    ) -> Visit | None:
        """before 전에 시작한 마지막 완료 방문. pet_id 가 있으면 그 아이의, 없으면 보호자만의 방문 가운데서."""

    @abstractmethod
    async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int: ...

    @abstractmethod
    async def list_between(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        """시작 시각이 [start, end) 인 방문 — 상태와 상관없이, 시작 순으로."""

    @abstractmethod
    async def unresolved_before(self, ctx: ShopContext, before: datetime) -> tuple[int, datetime | None]:
        """시작 시각이 before 전인데 아직 예약됨인 방문(정리 안 된 예약)의 수와 가장 이른 시작 시각."""

    @abstractmethod
    async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        """[start, end) 와 시간이 겹치는 살아 있는 방문(예약됨·미용 중)."""
