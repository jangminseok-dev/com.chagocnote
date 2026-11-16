from __future__ import annotations

from visit.adapter.outbound.orm.visit_orm import VisitReportOrm
from visit.domain.entities.visit_report import VisitReport


def to_report(orm: VisitReportOrm) -> VisitReport:
    return VisitReport(
        id=orm.id, visit_id=orm.visit_id, public_id=orm.public_id, expires_at=orm.expires_at,
        revoked_at=orm.revoked_at, first_viewed_at=orm.first_viewed_at,
        created_by_member_id=orm.created_by_member_id, created_at=orm.created_at, show_review=orm.show_review,
    )
