"""메시지 상태와 취소 이유·오류 종류·나간 길(설계 4.4). STATUSES 의 순서가 ORM CHECK 의 순서다."""
SCHEDULED, SENDING, ACCEPTED, SENT, FALLBACK_SENT, FAILED, CANCELED = (
    "scheduled", "sending", "accepted", "sent", "fallback_sent", "failed", "canceled",
)
STATUSES: tuple[str, ...] = (SCHEDULED, SENDING, ACCEPTED, SENT, FALLBACK_SENT, FAILED, CANCELED)
PENDING_STATUSES = frozenset({SCHEDULED, SENDING})      # 부분 유일 색인의 조건 — 같은 방문·종류의 대기 줄은 하나
DELIVERED_STATUSES = frozenset({SENT, FALLBACK_SENT})   # "이미 보냈다"
CANCEL_REASONS: tuple[str, ...] = (
    "rescheduled", "visit_canceled", "no_show", "setting_off", "channel_unlinked",
    "shop_closed", "template_rejected", "report_revoked", "too_late", "anonymized",
    "has_upcoming", "cooldown", "no_consent", "bad_phone",
    "reverted", "passed_away",          # 0012 — 되돌린 완료의 다음 예약 제안, 무지개다리를 건넌 아이
)
ERROR_KINDS: tuple[str, ...] = ("transient", "permanent")
CHANNELS_USED: tuple[str, ...] = ("alimtalk", "sms", "lms")
