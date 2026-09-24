from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.record_input import RecordInput


@dataclass(frozen=True)
class PutVisitRecordCommand:
    """기록 전체 교체. version 은 기록이 없으면 None, 있으면 읽었을 때의 버전이다."""

    ctx: ShopContext
    visit_id: int
    version: int | None
    record: RecordInput
