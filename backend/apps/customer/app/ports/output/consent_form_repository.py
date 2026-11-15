from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from customer.domain.entities.consent_form import ConsentForm
from hub.app.dtos.shop_context import ShopContext


class ConsentFormRepository(ABC):
    """동의서 요청(customer_forms 의 kind='consent')의 저장소.

    find_public·lock·mark_submitted 만 ShopContext 를 받지 않는다 — 서명을 확인한 public_id(와 거기서 읽은 요청)로만 부른다.
    """

    @abstractmethod
    async def create(
        self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...], public_id: bytes,
        expires_at: datetime,
    ) -> ConsentForm: ...

    @abstractmethod
    async def live_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> list[ConsentForm]:
        """그 고객의 살아 있는 요청. 행을 잠근다 — 고객 행을 이미 쥔 안에서 부른다."""

    @abstractmethod
    async def list_live(self, ctx: ShopContext, now: datetime) -> list[ConsentForm]:
        """이 매장의 살아 있는 요청. 보낸 날 내림차순."""

    @abstractmethod
    async def get(self, ctx: ShopContext, form_id: int) -> ConsentForm:
        """없거나 다른 매장의 것이면 FormNotFoundError."""

    @abstractmethod
    async def revoke(self, ctx: ShopContext, form_id: int, now: datetime) -> None:
        """끊는다. 이미 끊었거나 낸 요청은 그대로 둔다."""

    @abstractmethod
    async def close_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        """그 고객의 요청을 전부 닫는다 — 이미 낸 것도(익명화). 낸 링크가 "보냈어요"로도 열리지 않는다."""

    @abstractmethod
    async def set_pets(self, ctx: ShopContext, form_id: int, pet_ids: tuple[int, ...]) -> None:
        """요청이 담는 아이를 바꾼다."""

    @abstractmethod
    async def sent_on(self, ctx: ShopContext, pet_ids: tuple[int, ...], now: datetime) -> dict[int, datetime]:
        """아이 → 그 아이를 담은 살아 있는 요청을 보낸 시각. 없는 아이는 빠진다."""

    @abstractmethod
    async def find_public(self, public_id: bytes) -> ConsentForm | None:
        """매장을 가리지 않는 공개 읽기."""

    @abstractmethod
    async def lock(self, form_id: int) -> ConsentForm | None:
        """요청 행을 잠그고 다시 읽는다."""

    @abstractmethod
    async def mark_submitted(self, form_id: int, now: datetime) -> None: ...
