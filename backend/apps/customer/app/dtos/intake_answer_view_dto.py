from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from customer.domain.entities.intake import IntakeAnswer


@dataclass(frozen=True)
class IntakeConsentSummary:
    """맡아 둔 서명의 요약 — 그림과 적은 이름은 싣지 않는다."""

    signed_on: date                      # 매장 시간대의 날
    parts: tuple[str, ...]               # 보호자가 읽은 토막


@dataclass(frozen=True)
class IntakeAnswerView:
    """받은 문진표 한 장. 매장 멤버만 본다 — 이름·번호·적은 글을 로그에 남기지 않는다."""

    answer: IntakeAnswer
    pet_name: str | None                 # 답에 적은 이름, 다시 받기면 그 아이의 지금 이름
    submitted_on: date                   # 매장 시간대의 날
    matched_customer_name: str | None
    condition_labels: dict[str, str]     # 지병 종류 코드 → 이름
    missing: tuple[str, ...]
    memo_draft: str
    memo_over: int
    consent: IntakeConsentSummary | None = None    # 끝의 동의서에서 맡아 둔 서명(⑪-C1b)
