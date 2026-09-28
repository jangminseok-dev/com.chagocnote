from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from visit.app.dtos.report_view_dto import ReportView


@dataclass(frozen=True)
class ReadPublicReportQuery:
    token: str | None     # X-Report-Token 헤더 그대로. 없거나 이상해도 받는다 — 판정은 유스케이스가 한다
    client: str           # 횟수를 셀 접속 주소


@dataclass(frozen=True)
class PublicReportView:
    report: ReportView              # 뺀 사진·영상은 없다
    expires_at: datetime | None     # 링크가 닫히는 시각(매장 시간대). None 이면 기간이 없다
