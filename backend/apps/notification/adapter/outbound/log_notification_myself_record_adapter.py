from __future__ import annotations

import logging

from notification.app.ports.output.notification_myself_record_port import NotificationMyselfRecordPort

logger = logging.getLogger(__name__)


class LogNotificationMyselfRecordAdapter(NotificationMyselfRecordPort):
    """기록을 로그로 남기는 구현. 매장·고객 정보는 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[notification-myself-record] %s | %s", subject, note)
