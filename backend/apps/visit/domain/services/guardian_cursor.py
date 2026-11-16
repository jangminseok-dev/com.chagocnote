"""보호자용 알림장 목록의 쪽 표시 — 마지막 줄의 (방문 시작 시각, 방문 ID). 불투명한 글자로 주고받는다."""
from __future__ import annotations

import base64
from datetime import datetime, timezone

from visit.domain.errors import VisitInputError


def encode_cursor(starts_at: datetime, visit_id: int) -> str:
    raw = f"{starts_at.isoformat()}|{visit_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    """깨진 글자면 VisitInputError(422) — 어떤 입력에도 다른 예외를 던지지 않는다."""
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        starts_at, visit_id = raw.split("|")
        at = datetime.fromisoformat(starts_at)
        if at.tzinfo is None or not 0 < int(visit_id) <= 2_147_483_647:
            raise ValueError(cursor)
        # UTC 로 바꿔 둔다 — 바꾸면 범위를 넘는 시각(연도 1·9999 근처)은 DB 바인딩이 아니라 여기서 걸린다.
        return at.astimezone(timezone.utc), int(visit_id)
    except (ValueError, UnicodeError, OverflowError) as exc:
        raise VisitInputError("목록을 이어서 불러올 수 없습니다. 처음부터 다시 불러 주세요.") from exc


# --- 모아 보기(⑫)의 쪽 표시 — 마지막 미디어의 (방문 시작 시각, 방문 ID, 전후, 순서) ---

MediaCursor = tuple[datetime, int, str, int]


def encode_media_cursor(starts_at: datetime, visit_id: int, phase: str, sort_order: int) -> str:
    raw = f"{starts_at.isoformat()}|{visit_id}|{phase}|{sort_order}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_media_cursor(cursor: str) -> MediaCursor:
    """깨진 글자면 VisitInputError(422)."""
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        starts_at, visit_id, phase, sort_order = raw.split("|")
        at = datetime.fromisoformat(starts_at)
        if at.tzinfo is None or not 0 < int(visit_id) <= 2_147_483_647 or phase not in ("after", "before"):
            raise ValueError(cursor)
        if not 0 <= int(sort_order) < 1000:
            raise ValueError(cursor)
        return at.astimezone(timezone.utc), int(visit_id), phase, int(sort_order)
    except (ValueError, UnicodeError, OverflowError) as exc:
        raise VisitInputError("목록을 이어서 불러올 수 없습니다. 처음부터 다시 불러 주세요.") from exc

