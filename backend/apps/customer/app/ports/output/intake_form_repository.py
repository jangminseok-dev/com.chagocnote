from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from customer.domain.entities.intake import IntakeForm
from hub.app.dtos.shop_context import ShopContext


class IntakeFormRepository(ABC):
    """문진표 요청(customer_forms 의 kind='intake')의 저장소.

    find_public·lock·mark_submitted 만 ShopContext 를 받지 않는다 — 서명을 확인한 public_id(와 거기서 읽은 요청)로만 부른다.
    """

    @abstractmethod
    async def create(
        self, ctx: ShopContext, customer_id: int | None, pet_id: int | None, public_id: bytes, expires_at: datetime,
    ) -> IntakeForm: ...

    @abstractmethod
    async def live_for(self, ctx: ShopContext, customer_id: int, pet_id: int | None, now: datetime) -> IntakeForm | None:
        """그 고객의 새 아이용(pet_id 없음) 또는 그 아이의 다시 받기용 살아 있는 요청. 고객 행을 쥔 안에서 부른다."""

    @abstractmethod
    async def close_expired(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        """그 고객의, 내지도 끊지도 않은 채 기간이 지난 요청을 닫는다. 새로 보내기 전에 부른다 — 아이마다 열린 요청이
        하나라는 색인은 기간을 모른다."""

    @abstractmethod
    async def list_live(self, ctx: ShopContext, now: datetime) -> list[IntakeForm]:
        """이 매장의 살아 있는 요청. 보낸 날 내림차순."""

    @abstractmethod
    async def get(self, ctx: ShopContext, form_id: int) -> IntakeForm | None:
        """없거나 다른 매장의 것이거나 문진표가 아니면 None."""

    @abstractmethod
    async def revoke(self, ctx: ShopContext, form_id: int, now: datetime) -> None:
        """끊는다. 이미 끊었거나 다 적은 요청은 그대로 둔다."""

    @abstractmethod
    async def close_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        """그 고객의 요청을 전부 닫는다 — 다 적은 것도(익명화)."""

    @abstractmethod
    async def close_for_pet(self, ctx: ShopContext, pet_id: int, now: datetime, *, detach: bool) -> None:
        """그 아이의 다시 받기 요청을 닫는다. detach 면 아이와의 이음도 끊는다(아이를 지울 때 — 행이 아이를 가리킨다)."""

    @abstractmethod
    async def find_public(self, public_id: bytes) -> IntakeForm | None:
        """매장을 가리지 않는 공개 읽기."""

    @abstractmethod
    async def lock(self, form_id: int) -> IntakeForm | None:
        """요청 행을 잠그고 다시 읽는다."""

    @abstractmethod
    async def mark_submitted(self, form_id: int, now: datetime) -> None: ...
