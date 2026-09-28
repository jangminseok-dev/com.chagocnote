from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

BEFORE = "before"
AFTER = "after"
PHASES = (BEFORE, AFTER)
PAYMENT_METHODS = ("card", "cash", "transfer")


@dataclass(frozen=True)
class RecordItem:
    """실제로 한 메뉴 하나와 그 금액(원). 예약 메뉴(visit_menus)는 계획이고 이것은 실적이다."""

    menu_id: int
    amount: int


@dataclass(frozen=True)
class RecordMedia:
    """기록에 붙은 사진·영상 하나. kind 는 media 가 가져가기(claim) 때 알려 준 값이다 — 바뀌지 않는 사실이라
    옮겨 적어 두고 대표 사진·한도를 이 표만으로 계산한다."""

    media_id: int
    kind: str       # photo · video
    phase: str      # before · after
    sort_order: int
    hidden: bool = False   # ⑤ 알림장에서 뺀 사진


@dataclass(frozen=True)
class VisitRecord:
    """방문 하나의 미용 기록(설계 6.1). 총액은 항목 합에서 나오지 않는 별개 사실(받은 돈)이다.

    version 은 기록을 바꿀 때마다 1씩 오른다 — 전체 교체(PUT)가 모르는 사이 붙은 사진을 지우지 않게 한다.
    """

    visit_id: int
    weight_kg: Decimal | None
    care_note: str | None       # 공개 — ⑤ 알림장에 실린다
    internal_note: str | None   # 매장 안에서만
    payment_method: str | None
    total_amount: int | None
    items: tuple[RecordItem, ...]
    media: tuple[RecordMedia, ...]
    version: int
    created_by_member_id: int
    updated_by_member_id: int
