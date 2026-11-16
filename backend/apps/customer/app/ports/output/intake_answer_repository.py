from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from customer.domain.entities.intake import IntakeAnswer
from customer.domain.services.intake_rules import CleanAnswer
from hub.app.dtos.shop_context import ShopContext


class IntakeAnswerRepository(ABC):
    """받은 문진표. 이름·번호·적은 글은 개인정보다 — 로그에 남기지 않고 등록·지우기·기한에서 지운다."""

    @abstractmethod
    async def add(
        self, ctx: ShopContext, form_id: int, answer: CleanAnswer, matched_customer_id: int | None, now: datetime,
    ) -> int:
        """답을 쓰고 요청의 받은 수를 하나 올린다."""

    @abstractmethod
    async def first_guardian(self, form_id: int) -> tuple[str, str] | None:
        """그 링크로 받은 답 가운데 보호자를 적은 가장 앞의 것 (이름, 번호). 둘째 답부터 이것을 쓴다.
        그 답을 이미 등록·지웠으면 None — 그때는 보호자를 다시 묻는다."""

    @abstractmethod
    async def list_since(self, ctx: ShopContext, since: datetime) -> list[IntakeAnswer]:
        """since 뒤에 받은 답(보관 기간 안의 것), 받은 시각 내림차순."""

    @abstractmethod
    async def get(self, ctx: ShopContext, answer_id: int, since: datetime) -> IntakeAnswer | None:
        """없거나 다른 매장의 것이거나 보관 기간이 지났으면 None."""

    @abstractmethod
    async def target_of(self, ctx: ShopContext, answer_id: int) -> tuple[int | None, int | None] | None:
        """그 답을 받은 링크의 (고객, 아이). 새 손님용이면 둘 다 None. 답이 없거나 다른 매장의 것이면 None."""

    @abstractmethod
    async def delete(self, ctx: ShopContext, answer_id: int) -> bool:
        """지웠으면 True. 없거나 다른 매장의 것이면 False — 등록이 같은 답을 두 번 쓰지 못한다."""

    @abstractmethod
    async def delete_for_customer(self, ctx: ShopContext, customer_id: int, phones: tuple[str, ...] = ()) -> None:
        """그 고객에 이어 둔 답, 그 고객에게 보낸 링크의 답, 그 고객의 번호(phones — 숫자만)를 적어 낸 답(익명화).
        낼 때는 고객이 없어 이어지지 않은 답에도 그 보호자의 이름·번호가 들어 있다."""

    @abstractmethod
    async def delete_for_pet(self, ctx: ShopContext, pet_id: int) -> None:
        """그 아이의 정보를 다시 받은 답(아이를 지울 때)."""

    @abstractmethod
    async def delete_older(self, ctx: ShopContext, before: datetime) -> int:
        """before 보다 앞서 받은 답을 지우고 그 수를 돌려준다(주기 작업)."""

    @abstractmethod
    async def shops_with_answers(self) -> list[int]:
        """받은 답이 있는 매장 — 주기 작업이 매장마다 보관 기간을 읽으려고 쓴다. 매장을 가리지 않는 유일한 읽기다."""
