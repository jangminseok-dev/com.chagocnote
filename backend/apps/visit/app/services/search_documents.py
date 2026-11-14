"""방문 하나에서 검색에 넣을 글을 고른다(⑨ 설계 3.2) — 케어 노트, 내부 메모, 예약 메모. 글을 로그에 남기지 않는다."""
from __future__ import annotations

from zoneinfo import ZoneInfo

from hub.app.dtos.search_source import SourceDocument
from visit.domain.entities.visit import Visit
from visit.domain.entities.visit_record import VisitRecord


def visit_documents(visit: Visit, record: VisitRecord | None, timezone: str) -> list[SourceDocument]:
    """빈 글·공백뿐인 글은 문서가 아니다. 방문의 상태는 가리지 않는다(취소한 예약의 메모도 찾아진다).
    날짜는 매장 시간대의 방문 날이다."""
    happened_on = visit.starts_at.astimezone(ZoneInfo(timezone)).date()
    texts = (
        ("care_note", record.care_note if record else None),
        ("internal_note", record.internal_note if record else None),
        ("visit_memo", visit.memo),
    )
    return [
        SourceDocument(kind=kind, source_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
                       visit_id=visit.id, happened_on=happened_on, body=text.strip())
        for kind, text in texts
        if text and text.strip()
    ]
