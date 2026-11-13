from __future__ import annotations

import logging

from guardian.app.ports.output.guardian_myself_record_port import GuardianMyselfRecordPort

logger = logging.getLogger(__name__)


class LogGuardianMyselfRecordAdapter(GuardianMyselfRecordPort):
    """기록을 로그로 남기는 구현. 매장·고객 정보는 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[guardian-myself-record] %s | %s", subject, note)
