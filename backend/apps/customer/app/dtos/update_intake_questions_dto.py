from __future__ import annotations

from dataclasses import dataclass

from customer.domain.entities.intake import QuestionDraft
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateIntakeQuestionsCommand:
    ctx: ShopContext
    questions: tuple[QuestionDraft, ...]
