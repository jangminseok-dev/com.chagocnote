"""문진표의 값들(⑪ 설계 3.4)."""
from __future__ import annotations

from dataclasses import dataclass

QUESTION_MAX = 5
QUESTION_LABEL_MAX = 100


@dataclass(frozen=True)
class IntakeQuestion:
    """매장이 문진표에 더한 질문 하나."""

    id: int
    label: str
    required: bool


@dataclass(frozen=True)
class QuestionDraft:
    """저장할 질문. id 가 있으면 있던 질문을 고치고, 없으면 새로 더한다."""

    id: int | None
    label: str
    required: bool
