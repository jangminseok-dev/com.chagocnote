from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from customer.domain.entities.consent import SignedCover
from customer.domain.entities.consent_form import HeldConsent, HeldSignature, NewSignature, SignatureBrief, SignatureDetail
from hub.app.dtos.shop_context import ShopContext


class ConsentSignatureRepository(ABC):
    """동의서 서명의 저장소. 그림·적은 이름·보인 사실은 개인정보다."""

    @abstractmethod
    async def add(self, ctx: ShopContext, signature: NewSignature) -> int:
        """서명 한 번과 그 아래 줄을 쓰고 서명 ID 를 돌려준다."""

    @abstractmethod
    async def covers(self, ctx: ShopContext, since: Mapping[int, int]) -> dict[int, tuple[SignedCover, ...]]:
        """아이 → 그 아이의 받은 날을 찍은 서명(since, 서명 ID)부터의 서명들이 덮은 것, 받은 순서대로.

        날짜가 아니라 서명 ID 로 거른다 — 같은 날 지우고 다시 받았을 때 지우기 전의 서명이 끼지 않고,
        시각과 날짜를 따로 읽어 생기는 하루의 어긋남이 없다. 서명이 없는 아이는 빠진다.
        """

    @abstractmethod
    async def list_for_pet(self, ctx: ShopContext, pet_id: int) -> list[SignatureBrief]:
        """새것부터."""

    @abstractmethod
    async def get(self, ctx: ShopContext, signature_id: int) -> SignatureDetail:
        """없거나 다른 매장의 것이면 SignatureNotFoundError."""

    @abstractmethod
    async def image(self, ctx: ShopContext, signature_id: int) -> bytes:
        """서명 그림. 없거나 다른 매장의 것이면 SignatureNotFoundError."""

    @abstractmethod
    async def delete_for_customer(self, ctx: ShopContext, customer_id: int) -> int:
        """그 고객의 서명을 전부 지운다(익명화). 지운 서명 수."""

    @abstractmethod
    async def delete_for_pet(self, ctx: ShopContext, pet_id: int) -> int:
        """그 아이의 줄을 지우고, 아이가 남지 않은 서명도 지운다(반려동물 삭제). 지운 줄 수."""

    @abstractmethod
    async def adopt_held(
        self, ctx: ShopContext, answer_id: int, *, customer_id: int, pet_id: int,
    ) -> HeldSignature | None:
        """그 답에 맡아 둔 서명을 그 고객·아이에게 옮겨 붙인다(답에서 떼어 낸다). 없으면 None."""

    @abstractmethod
    async def held_for(self, ctx: ShopContext, answer_ids: list[int]) -> dict[int, HeldConsent]:
        """답마다 맡아 둔 서명의 요약."""

