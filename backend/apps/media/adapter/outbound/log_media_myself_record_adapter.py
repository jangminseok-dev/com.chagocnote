from __future__ import annotations

import logging

from media.app.ports.output.media_myself_record_port import MediaMyselfRecordPort

logger = logging.getLogger(__name__)


class LogMediaMyselfRecordAdapter(MediaMyselfRecordPort):
    """기록을 로그로 남기는 구현. 객체 키·URL 은 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[media-myself-record] %s | %s", subject, note)
