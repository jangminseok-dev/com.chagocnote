from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

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


# --- 모아 보기(⑫ 설계 3.3·3.4) ---

@dataclass(frozen=True)
class SentMedia:
    """보호자가 볼 수 있는 알림장에 나오는 미디어 한 줄(뺀 것·끊은 알림장의 것은 없다)."""

    report_id: int
    visit_id: int
    starts_at: datetime
    media_id: int
    kind: str
    phase: str
    sort_order: int


@dataclass(frozen=True)
class ListGuardianMediaQuery:
    guardian: GuardianContext
    pet_id: int | None
    year: int | None
    phase: str | None
    cursor: str | None


@dataclass(frozen=True)
class GuardianMediaItemView:
    report_id: int
    visit_date: date
    kind: str
    phase: str
    width: int
    height: int
    duration_seconds: int | None
    display_url: str
    thumb_url: str
    download_url: str


@dataclass(frozen=True)
class GuardianMediaPageView:
    items: tuple[GuardianMediaItemView, ...]
    next_cursor: str | None
    years: tuple[int, ...]           # 받은 알림장이 있는 해(최근부터) — 아이를 골랐으면 그 아이의


@dataclass(frozen=True)
class ReadGuardianWeightsQuery:
    guardian: GuardianContext
    pet_id: int


@dataclass(frozen=True)
class GuardianWeightView:
    visit_date: date
    weight_kg: Decimal

