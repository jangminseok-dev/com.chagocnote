from __future__ import annotations

import logging

from tenancy.app.ports.output.tenancy_myself_record_port import TenancyMyselfRecordPort

logger = logging.getLogger(__name__)


class LogTenancyMyselfRecordAdapter(TenancyMyselfRecordPort):
    """기록을 로그로 남기는 구현. 영속 기록이 필요해지면 PG 어댑터로 바꾼다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[tenancy-myself-record] %s | %s", subject, note)
