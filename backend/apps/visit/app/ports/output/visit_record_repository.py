from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit_record import VisitRecord


class VisitRecordRepository(ABC):
    """미용 기록(visit_records 와 항목·미디어 두 하위 표). 읽기는 방문의 매장(ShopContext)으로 거른다.

    쓰기는 방문 행을 잠근 **뒤에만** 부른다 — 방문이 이 매장의 것임은 잠금(`lock_visits`)이 이미 확인했다.
    """

    @abstractmethod
    async def get(self, ctx: ShopContext, visit_id: int) -> VisitRecord | None:
        """없거나 다른 매장의 방문이면 None."""

    @abstractmethod
    async def list_many(self, ctx: ShopContext, visit_ids: list[int]) -> dict[int, VisitRecord]:
        """기록이 있는 방문마다 기록 전체. 기록이 없는 방문은 키가 없다 — 상세·목록·달력의 '기록 있음'과
        대표 사진을 방문 수와 상관없이 한 번에 읽는다."""

    @abstractmethod
    async def latest_with_media(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
        """{반려동물 ID: 방문 ID} — 사진·영상이 붙은 기록이 있는 가장 최근(시작 시각) 완료 방문."""

    @abstractmethod
    async def clear_notes(self, ctx: ShopContext, customer_id: int) -> None:
        """그 보호자의 방문 기록들의 케어 메모·내부 메모를 비운다(익명화)."""

    @abstractmethod
    async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
        """행이 없으면 넣고 있으면 바꾼다. 항목·미디어는 통째로 바꾼다. 버전은 부르는 쪽이 정해 넘긴다.
        미디어의 뺀 표시(hidden)도 넘긴 그대로 쓴다 — 앞선 표시를 이어 붙이는 것은 부르는 쪽의 일이다."""

    @abstractmethod
    async def set_hidden(self, ctx: ShopContext, visit_id: int, hidden_ids: tuple[int, ...]) -> None:
        """그 기록의 미디어 전부에 뺀 표시를 다시 매긴다 — hidden_ids 에 있으면 뺀 것, 없으면 보이는 것.

        기록 버전은 올리지 않는다. 뺀 표시는 앱의 폼 저장(PUT)이 모르고 지울 값이 아니다 — 폼은 이 값을 보내지
        않고 서버가 미디어 ID 로 이어 붙인다."""

    @abstractmethod
    async def delete(self, ctx: ShopContext, visit_id: int) -> None:
        """기록 행을 지운다. 항목·미디어 연결은 외래 키의 ON DELETE CASCADE 로 함께 지워진다."""
