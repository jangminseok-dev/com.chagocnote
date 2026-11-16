from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from hub.app.dtos.bundle_texts import BundleTexts, ConsentLink
from hub.app.dtos.shop_context import ShopContext


class GuardianFormPort(ABC):
    """구현: customer. 사용: visit(예약의 보낼 것 묶음). 보호자에게 보낼 서류 링크와 보내는 글의 템플릿."""

    @abstractmethod
    async def consent_link(self, ctx: ShopContext, pet_ids: tuple[int, ...], for_date: date) -> ConsentLink | None:
        """그 아이들(한 가족)의 동의서 링크. 살아 있는 요청이 있으면 그것이고 없으면 만든다 — 다시 불러도 같은 주소다.
        더 받을 것이 없거나 보낼 수 없는 아이(익명화한 고객·무지개다리)면 None.
        고객 행 → 서류 요청 행을 잠근다 — 부르는 쪽은 방문 행을 쥐고 있지 않아야 한다. 주소를 로그에 남기지 않는다."""

    @abstractmethod
    async def bundle_texts(self, ctx: ShopContext) -> BundleTexts:
        """매장의 보내는 글. 잠그지 않는다."""
