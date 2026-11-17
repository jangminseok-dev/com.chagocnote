from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.check_view_dto import CheckView
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
class SeriesBriefView:
    """반복 묶음 한 줄(⑭) — `4주마다 · 6번 중 3번째`. 자리는 취소를 뺀 회차(가족은 한 번)로 센다."""

    id: int
    interval_weeks: int
    position: int
    total: int
    is_last: bool


@dataclass(frozen=True)
class VisitDetailView:
    visit: VisitView
    group: list[VisitView]                 # 같은 묶음의 다른 방문(같은 보호자 + 같은 시작 시각)
    previous_visit: PreviousVisitView | None   # 그 아이(보호자만이면 보호자)의 지난 완료 방문
    no_show_count: int                     # 이 보호자의 노쇼 횟수
    record: RecordView | None              # 미용 기록 — 없으면 None
    cover: str | None                      # 대표 사진 썸네일(후 → 전 → 영상 포스터)
    report: ReportLinkView                 # 알림장 링크의 상태 — 보낸 적이 없거나 닫혔으면 none
    checks: list[CheckView] = field(default_factory=list)   # 확인할 것(③-B) — 살아 있는 방문만, 그 밖은 빈 목록
    marks: list[str] = field(default_factory=list)   # 끝낸 일의 낱말 코드(⑬) — 이름 카드가 쓴다
    report_skipped: bool = False                     # 하루 마무리에서 알림장을 보내지 않음으로 넘겼다(⑬)
    series: SeriesBriefView | None = None            # 반복 묶음에 든 예약이면(⑭)
