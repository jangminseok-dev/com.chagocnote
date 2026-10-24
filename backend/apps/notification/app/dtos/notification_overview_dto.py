from __future__ import annotations

from dataclasses import dataclass

from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate


@dataclass(frozen=True)
class NotificationOverviewView:
    """설정 화면의 한눈에 보기 — 연동·설정·발신번호 인증의 명령도 이것을 돌려준다."""

    channel: NotificationChannel | None       # 연동을 시작한 적이 없으면 None
    settings: NotificationSettings | None     # 연동 전엔 None
    templates: list[NotificationTemplate]     # 종류 순
