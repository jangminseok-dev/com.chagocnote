from __future__ import annotations

from abc import ABC, abstractmethod

from customer.domain.entities.intake import IntakeQuestion, QuestionDraft
from hub.app.dtos.shop_context import ShopContext


class IntakeQuestionRepository(ABC):
    """매장이 문진표에 더한 질문."""

    @abstractmethod
    async def list_live(self, ctx: ShopContext) -> list[IntakeQuestion]:
        """지우지 않은 질문. 정한 순서대로."""

    @abstractmethod
    async def replace_all(self, ctx: ShopContext, drafts: tuple[QuestionDraft, ...]) -> list[IntakeQuestion]:
        """목록 전체를 바꾼다 — 있던 질문은 글·순서를 고치고, 빠진 질문은 지운 것으로 적고(행은 남긴다), 새 질문을 더한다."""
