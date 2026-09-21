from __future__ import annotations

from abc import ABC, abstractmethod


class TenancyMyselfRecordPort(ABC):
    """자기소개 조회 기록. 구현(로그 또는 DB)은 어댑터가 제공한다."""

    @abstractmethod
    async def record(self, subject: str, note: str) -> None: ...
