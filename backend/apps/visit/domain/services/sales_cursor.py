"""매출 탭에서 이어지는 목록의 쪽 표시. 불투명한 글자로 주고받고, 깨진 글자는 무엇이든 422 다."""
from __future__ import annotations

import base64
from datetime import date, datetime

from visit.domain.errors import VisitInputError
from visit.domain.services.guardian_cursor import decode_cursor, encode_cursor

_MAX_ID = 9_223_372_036_854_775_807


def encode_visit_cursor(starts_at: datetime, visit_id: int) -> str:
    """방문 목록 — 마지막 줄의 (시작 시각, 방문 ID). 보호자용 목록과 같은 모양이다."""
    return encode_cursor(starts_at, visit_id)


def decode_visit_cursor(cursor: str) -> tuple[datetime, int]:
    return decode_cursor(cursor)


def encode_due_cursor(last_day: date, pet_id: int) -> str:
    """다시 올 때가 지난 아이 — 마지막 줄의 (마지막 방문일, 반려동물 ID)."""
    return base64.urlsafe_b64encode(f"{last_day.isoformat()}|{pet_id}".encode()).decode().rstrip("=")


def decode_due_cursor(cursor: str) -> tuple[date, int]:
    """깨진 글자면 VisitInputError(422) — 어떤 입력에도 다른 예외를 던지지 않는다."""
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        day, pet_id = raw.split("|")
        if len(day) != 10 or not 0 < int(pet_id) <= _MAX_ID:
            raise ValueError(cursor)
        return date.fromisoformat(day), int(pet_id)
    except (ValueError, UnicodeError, OverflowError) as exc:
        raise VisitInputError("목록을 이어서 불러올 수 없습니다. 처음부터 다시 불러 주세요.") from exc
