from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

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
