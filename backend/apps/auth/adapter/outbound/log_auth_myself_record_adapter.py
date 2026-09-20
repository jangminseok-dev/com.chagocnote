from __future__ import annotations

import logging

from auth.app.ports.output.auth_myself_record_port import AuthMyselfRecordPort

logger = logging.getLogger(__name__)


class LogAuthMyselfRecordAdapter(AuthMyselfRecordPort):
    """기록을 로그로 남기는 구현. 영속 기록이 필요해지면 PG 어댑터로 바꾼다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[auth-myself-record] %s | %s", subject, note)
