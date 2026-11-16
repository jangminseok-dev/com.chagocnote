from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CheckSchema(BaseModel):
    """확인할 것 하나(③-B). 매장용 응답에만 있다 — 공개·보호자 스키마에는 이 칸이 없다.

    detail 의 칸은 code 마다 다르다: caution {reason, until} · no_show {count} · first_visit {} ·
    consent {reasons, state(missing·expired·partial), received_on, parts(partial 일 때), form_sent_on(살아 있는 링크가 있을 때)} · conditions {items: [{label, note}]} · long_absence {days, last_visit_on}.
    """

    code: str
    scope: str
    detail: dict[str, Any]
