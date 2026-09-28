from __future__ import annotations

from dataclasses import dataclass

from visit.domain.entities.visit import Visit
from visit.domain.entities.visit_report import VisitReport


@dataclass(frozen=True)
class ReportTarget:
    """토큰이 가리키는 링크와 그 방문. shop_id 로 ShopContext 없이 시작한 공개 조회가 매장을 안다."""

    report: VisitReport
    shop_id: int
    visit: Visit
