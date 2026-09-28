from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkReportViewedCommand:
    token: str | None     # X-Report-Token 헤더 그대로
    client: str           # 횟수를 셀 접속 주소
