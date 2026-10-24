"""메시지 종류(설계 4.3·6.3). KINDS 의 순서가 ORM CHECK 의 순서다."""
CONFIRM, REMINDER, REPORT, CHANGE, CANCEL, NEXT_VISIT = (
    "confirm", "reminder", "report", "change", "cancel", "next_visit",
)
KINDS: tuple[str, ...] = (CONFIRM, REMINDER, REPORT, CHANGE, CANCEL, NEXT_VISIT)
DEFAULT_KINDS: tuple[str, ...] = tuple(k for k in KINDS if k != NEXT_VISIT)   # 연동 때 자동 등록하는 템플릿
SCHEDULED_KINDS = frozenset({REMINDER, NEXT_VISIT})                            # 시각이 있는 것 — 야간 미룸 대상
