from __future__ import annotations

import logging

from customer.app.ports.output.customer_myself_record_port import CustomerMyselfRecordPort

logger = logging.getLogger(__name__)


class LogCustomerMyselfRecordAdapter(CustomerMyselfRecordPort):
    """기록을 로그로 남기는 구현. 고객 정보는 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[customer-myself-record] %s | %s", subject, note)
