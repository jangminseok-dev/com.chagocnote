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
