"""문진표의 값들(⑪ 설계 3.4)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

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
    answered: int = 0          # 이 링크로 받은 답의 수(지운 것도 센다)

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


@dataclass(frozen=True)
class AnswerCondition:
    type_code: str
    custom_label: str | None
    note: str | None


@dataclass(frozen=True)
class IntakeAnswer:
    """받은 문진표 하나(아이 한 마리). 끈 칸·모르겠어요·묻지 않은 칸은 None 이다."""

    id: int
    form_id: int
    mode: str                          # 그 링크의 보내는 곳(new·add_pet·update)
    pet_id: int | None                 # 다시 받기일 때 — 그 아이
    matched_customer_id: int | None    # 미리 이어 둔 고객(번호가 같거나, 그 고객에게 보낸 링크)
    guardian_name: str | None
    guardian_phone: str | None
    pet_name: str | None
    species: str | None
    breed: str | None
    sex: str | None
    neutered: bool | None
    birth_date: date | None
    birth_year: int | None
    birth_unknown: bool
    weight_kg: Decimal | None
    no_known_conditions: bool | None
    conditions: tuple[AnswerCondition, ...]
    dislikes: str | None
    style: str | None
    extras: tuple[tuple[str, str], ...]     # (질문 글, 답) — 지운 질문의 답도 그 글과 함께 보인다
    submitted_at: datetime
