from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.record_view_dto import RecordView
from visit.app.dtos.report_view_dto import ReportLinkView
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class GetVisitQuery:
    ctx: ShopContext
    visit_id: int


@dataclass(frozen=True)
class PreviousVisitView:
    visit_id: int
    starts_at: datetime   # 매장 시간대
    cover: str | None     # 그 방문 기록의 대표 사진 썸네일


@dataclass(frozen=True)
class VisitDetailView:
    visit: VisitView
    group: list[VisitView]                 # 같은 묶음의 다른 방문(같은 보호자 + 같은 시작 시각)
    previous_visit: PreviousVisitView | None   # 그 아이(보호자만이면 보호자)의 지난 완료 방문
    no_show_count: int                     # 이 보호자의 노쇼 횟수
    record: RecordView | None              # 미용 기록 — 없으면 None
    cover: str | None                      # 대표 사진 썸네일(후 → 전 → 영상 포스터)
    report: ReportLinkView                 # 알림장 링크의 상태 — 보낸 적이 없거나 닫혔으면 none
