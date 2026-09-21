from __future__ import annotations

import logging

from platform_admin.app.ports.output.platform_myself_record_port import PlatformMyselfRecordPort

logger = logging.getLogger(__name__)


class LogPlatformMyselfRecordAdapter(PlatformMyselfRecordPort):
    """기록을 로그로 남기는 구현. 영속 기록이 필요해지면 PG 어댑터로 바꾼다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[platform-myself-record] %s | %s", subject, note)
