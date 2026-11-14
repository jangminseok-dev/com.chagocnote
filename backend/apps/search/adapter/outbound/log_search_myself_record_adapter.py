from __future__ import annotations

import logging

from search.app.ports.output.search_myself_record_port import SearchMyselfRecordPort

logger = logging.getLogger(__name__)


class LogSearchMyselfRecordAdapter(SearchMyselfRecordPort):
    """기록을 로그로 남기는 구현. 매장·고객 정보는 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[search-myself-record] %s | %s", subject, note)
