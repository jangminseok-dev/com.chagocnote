from __future__ import annotations

from visit.adapter.outbound.orm.visit_orm import VisitRecordItemOrm, VisitRecordMediaOrm, VisitRecordOrm
from visit.domain.entities.visit_record import RecordItem, RecordMedia, VisitRecord


def to_record(
    row: VisitRecordOrm, items: list[VisitRecordItemOrm], media: list[VisitRecordMediaOrm]
) -> VisitRecord:
    return VisitRecord(
        visit_id=row.visit_id, weight_kg=row.weight_kg, care_note=row.care_note, internal_note=row.internal_note,
        payment_method=row.payment_method, total_amount=row.total_amount,
        items=tuple(RecordItem(menu_id=i.menu_id, amount=i.amount) for i in items),
        media=tuple(RecordMedia(media_id=m.media_id, kind=m.kind, phase=m.phase, sort_order=m.sort_order)
                    for m in media),
        version=row.version, created_by_member_id=row.created_by_member_id,
        updated_by_member_id=row.updated_by_member_id,
    )
