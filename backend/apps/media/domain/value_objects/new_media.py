from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewMedia:
    """발급할 미디어 하나 — 규칙(`media_rules.check_upload`)을 통과한 선언값."""

    kind: str
    content_type: str
    width: int
    height: int
    duration_seconds: int | None
    uploaded_by_member_id: int
