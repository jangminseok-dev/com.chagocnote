"""문진표의 값들(⑪ 설계 3.4)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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


NEW, ADD_PET, UPDATE = "new", "add_pet", "update"
ANSWERS_PER_FORM = 10


@dataclass(frozen=True)
class IntakeForm:
    """보호자에게 보낸 문진표 링크 하나. 토큰은 저장하지 않는다 — public_id 와 서버 키로 그때마다 계산한다.

    보내는 곳 셋: 새 손님(고객·아이 없음), 등록된 고객의 새 아이(고객), 이미 있는 아이의 정보를 다시 받기(고객·아이).
    """

    id: int
    shop_id: int
    public_id: bytes
    customer_id: int | None
    pet_id: int | None
    expires_at: datetime
    revoked_at: datetime | None
    submitted_at: datetime | None
    created_by_member_id: int
    created_at: datetime

    @property
    def mode(self) -> str:
        if self.pet_id is not None:
            return UPDATE
        return NEW if self.customer_id is None else ADD_PET

    def is_live(self, now: datetime) -> bool:
        return self.revoked_at is None and self.submitted_at is None and now < self.expires_at

    def is_closed(self, now: datetime) -> bool:
        """끊었거나 기간이 지났다. 다 적은 요청은 닫힌 것이 아니다 — "보냈어요"를 보여야 한다."""
        return self.revoked_at is not None or (self.submitted_at is None and now >= self.expires_at)
