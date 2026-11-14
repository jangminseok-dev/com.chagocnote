from __future__ import annotations

from dataclasses import dataclass

from visit.domain.value_objects.check_facts import Check


@dataclass(frozen=True)
class CheckView:
    """확인할 것 하나(③-B). detail 의 칸은 code 마다 다르다 — 주의 사유·지병 메모가 들 수 있어 로그에 남기지 않는다."""

    code: str     # caution · no_show · first_visit · consent · conditions · long_absence
    scope: str    # customer | pet
    detail: dict

    @classmethod
    def of(cls, check: Check) -> CheckView:
        return cls(code=check.code, scope=check.scope, detail=dict(check.detail))
