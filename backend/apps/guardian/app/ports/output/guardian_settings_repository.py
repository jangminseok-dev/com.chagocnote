from __future__ import annotations

from abc import ABC, abstractmethod


class GuardianSettingsRepository(ABC):
    """매장이 정하는 가족 수(guardian_shop_settings, ⑫ 8절). 행이 없으면 기본값이다."""

    @abstractmethod
    async def family_max(self, shop_id: int) -> int: ...

    @abstractmethod
    async def put_family_max(self, shop_id: int, family_max: int) -> int: ...
