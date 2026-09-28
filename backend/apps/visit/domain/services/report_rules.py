"""알림장의 규칙 — 링크 기간, 뺄 사진, 보호자에게 보이는 미디어와 대표, 보낼 수 있는가(설계 4·6절).

판단은 잠근 뒤 다시 읽은 방문과 기록으로 한다.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from visit.domain.entities.visit import COMPLETED, Visit
from visit.domain.entities.visit_record import AFTER, BEFORE, RecordMedia, VisitRecord
from visit.domain.errors import (
    ReportEmptyError,
    VisitInputError,
    VisitNoRecordYetError,
    VisitNotCompletedError,
)
from visit.domain.services.visit_record_rules import cover_media_id
from visit.domain.value_objects.report_settings import LINK_DAYS, ReportSettings

MAX_HIDDEN = 33   # 방문당 사진 30 + 영상 3


def expires_at_for(now: datetime, link_days: int | None) -> datetime | None:
    return now + timedelta(days=link_days) if link_days is not None else None


def check_settings(settings: ReportSettings) -> None:
    if settings.link_days is not None and settings.link_days not in LINK_DAYS:
        raise VisitInputError("링크 기간은 7일, 30일, 계속 가운데 하나여야 합니다.")


def check_hidden_ids(record: VisitRecord, hidden_ids: tuple[int, ...]) -> None:
    if len(hidden_ids) > MAX_HIDDEN or len(set(hidden_ids)) != len(hidden_ids):
        raise VisitInputError("뺄 사진·영상은 겹치지 않게 33개까지 고를 수 있습니다.")
    if not set(hidden_ids) <= {m.media_id for m in record.media}:
        raise VisitInputError("이 기록의 사진·영상만 뺄 수 있습니다.")


def hide(record: VisitRecord, hidden_ids: tuple[int, ...]) -> tuple[RecordMedia, ...]:
    """기록의 미디어 전부에 뺀 표시를 다시 매긴다 — 고른 것만 빠지고 나머지는 되살아난다."""
    return tuple(replace(m, hidden=m.media_id in hidden_ids) for m in record.media)


def carry_hidden(previous: tuple[RecordMedia, ...], media: tuple[RecordMedia, ...]) -> tuple[RecordMedia, ...]:
    """기록을 다시 저장할 때 앞선 뺀 표시를 미디어 ID 로 옮긴다. 새로 붙은 미디어는 보인다."""
    hidden = {m.media_id for m in previous if m.hidden}
    return tuple(replace(m, hidden=m.media_id in hidden) for m in media)


def visible_media(record: VisitRecord) -> tuple[RecordMedia, ...]:
    """보호자에게 보이는 미디어 — 빼지 않은 것. 후 → 전, 그 안에서 sort_order."""
    shown = (m for m in record.media if not m.hidden)
    return tuple(sorted(shown, key=lambda m: ({AFTER: 0, BEFORE: 1}[m.phase], m.sort_order)))


def report_cover_media_id(record: VisitRecord) -> int | None:
    return cover_media_id(visible_media(record))


def check_sendable(visit: Visit, record: VisitRecord | None, hidden_ids: tuple[int, ...]) -> None:
    if visit.status != COMPLETED:
        raise VisitNotCompletedError("완료한 방문에서만 알림장을 보낼 수 있습니다.")
    if record is None:
        raise VisitNoRecordYetError("기록을 먼저 남겨 주세요.")
    check_hidden_ids(record, hidden_ids)


def check_not_empty(record: VisitRecord, hidden_ids: tuple[int, ...]) -> None:
    """링크를 새로 만들 때만 본다 — 보낸 뒤 사진을 전부 빼거나 메모를 비우는 것은 막지 않는다."""
    has_media = any(m.media_id not in hidden_ids for m in record.media)
    has_note = bool(record.care_note and record.care_note.strip())
    if not has_media and not has_note:
        raise ReportEmptyError("보낼 사진·영상이나 케어 메모가 없습니다.")
