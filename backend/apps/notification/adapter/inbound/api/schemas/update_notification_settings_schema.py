from __future__ import annotations

from datetime import time
from typing import Annotated

from pydantic import BaseModel, Field, StrictBool, StrictInt, StringConstraints

from notification.domain.entities.notification_settings import NotificationSettings

# 분까지만 — "18:00". 범위(08:00~21:00)는 도메인 check_settings 가 본다.
ReminderTime = Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
# 0 이상 정수만 — 1~52·1~365 는 도메인이 본다.
Count = Annotated[StrictInt, Field(ge=0)]


class UpdateNotificationSettingsRequestSchema(BaseModel):
    """아홉 칸 모두 필수다(전체 교체). 주기를 비우면(null) 지난 방문 간격을 쓴다."""

    confirm_enabled: StrictBool
    reminder_enabled: StrictBool
    report_enabled: StrictBool
    change_enabled: StrictBool
    next_visit_enabled: StrictBool
    reminder_time: ReminderTime
    next_visit_after_weeks: Count | None
    next_visit_cooldown_days: Count
    sms_fallback_enabled: StrictBool

    def to_settings(self) -> NotificationSettings:
        hour, minute = self.reminder_time.split(":")
        return NotificationSettings(
            confirm_enabled=self.confirm_enabled, reminder_enabled=self.reminder_enabled,
            report_enabled=self.report_enabled, change_enabled=self.change_enabled,
            next_visit_enabled=self.next_visit_enabled, reminder_time=time(int(hour), int(minute)),
            next_visit_after_weeks=self.next_visit_after_weeks, next_visit_cooldown_days=self.next_visit_cooldown_days,
        )
