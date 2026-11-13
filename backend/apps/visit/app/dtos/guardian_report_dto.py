from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.guardian import GuardianContext
from visit.app.dtos.report_view_dto import ReportCoverView
from visit.domain.entities.visit import Visit
from visit.domain.entities.visit_report import VisitReport


@dataclass(frozen=True)
class SentReport:
    """보호자에게 보이는 알림장 한 줄과 그 방문 — 끊지 않았고(기간은 보지 않는다) 기록이 있다."""

    report: VisitReport
    visit: Visit


@dataclass(frozen=True)
class ListGuardianPetsQuery:
    guardian: GuardianContext


@dataclass(frozen=True)
class GuardianPetView:
    pet_id: int
    name: str | None


@dataclass(frozen=True)
class ListGuardianReportsQuery:
    guardian: GuardianContext
    pet_id: int | None
    cursor: str | None


@dataclass(frozen=True)
class GuardianReportItemView:
    report_id: int
    visit_date: date                 # 매장 시간대의 날짜
    pet_id: int | None               # 보호자만의 방문이면 None
    pet_name: str | None
    cover: ReportCoverView | None    # 대표 사진의 썸네일(영상이면 포스터). 뺀 것은 대표가 되지 않는다
    media_count: int                 # 뺀 것을 뺀 사진·영상 수


@dataclass(frozen=True)
class GuardianReportPageView:
    items: tuple[GuardianReportItemView, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class ReadGuardianReportQuery:
    guardian: GuardianContext
    report_id: int
