from __future__ import annotations

import logging

from visit.app.ports.output.visit_myself_record_port import VisitMyselfRecordPort

logger = logging.getLogger(__name__)


class LogVisitMyselfRecordAdapter(VisitMyselfRecordPort):
    """기록을 로그로 남기는 구현. 고객·방문 정보는 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[visit-myself-record] %s | %s", subject, note)
