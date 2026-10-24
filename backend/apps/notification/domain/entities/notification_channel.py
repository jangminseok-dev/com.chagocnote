from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from notification.domain.value_objects.channel_status import LINKED


@dataclass(frozen=True)
class NotificationChannel:
    """매장의 카카오톡 채널(발신프로필) 연동 한 줄(설계 4.1). 매장당 하나다."""

    shop_id: int
    status: str
    provider: str
    provider_channel_id: str | None
    linked_at: datetime | None
    unlinked_at: datetime | None
    sender_number: str | None                     # 문자 대체용 발신번호
    sender_number_verified_at: datetime | None    # 본인인증 전엔 None
    sms_fallback_enabled: bool

    @property
    def is_linked(self) -> bool:
        return self.status == LINKED

    @property
    def can_fallback(self) -> bool:
        """문자 대체는 켜져 있고 발신번호 인증을 마쳤을 때만(N11)."""
        return self.sms_fallback_enabled and self.sender_number_verified_at is not None
