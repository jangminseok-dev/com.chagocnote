from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT


@dataclass(frozen=True)
class NotificationSettings:
    """매장의 알림톡 설정(설계 4.2). 값 객체 성격이지만 매장당 한 줄이라 엔티티 자리에 둔다."""

    confirm_enabled: bool
    reminder_enabled: bool
    report_enabled: bool
    change_enabled: bool                 # change·cancel 둘을 켠다
    next_visit_enabled: bool
    reminder_time: time                  # 매장 시간대의 벽시계 시각
    next_visit_after_weeks: int | None   # None = 지난 방문 간격(없으면 4주)
    next_visit_cooldown_days: int

    def enabled_for(self, kind: str) -> bool:
        return {
            CONFIRM: self.confirm_enabled,
            REMINDER: self.reminder_enabled,
            REPORT: self.report_enabled,
            CHANGE: self.change_enabled,
            CANCEL: self.change_enabled,
            NEXT_VISIT: self.next_visit_enabled,
        }[kind]


DEFAULT_NOTIFICATION_SETTINGS = NotificationSettings(
    confirm_enabled=True, reminder_enabled=True, report_enabled=True, change_enabled=True,
    next_visit_enabled=False, reminder_time=time(18, 0), next_visit_after_weeks=None,
    next_visit_cooldown_days=30,
)
