"""동의서의 값들(⑪ 설계 3.2·3.3). 전부 바뀌지 않는 값이다."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ConsentPolicy:
    """동의의 기준값. 기본값은 ③-B 의 판정과 같다 — 매장이 바꾸는 값은 ⑪-B 가 여기에 넣는다."""

    senior_age: int = 10      # 살 — 이 나이부터 노령 토막이 붙는다
    consent_days: int = 365   # 받은 날로부터 이 날 수째까지 유효


@dataclass(frozen=True)
class SignedCover:
    """서명 하나가 한 아이에 대해 덮은 것 — 읽은 토막과 그때 보인 지병 이름."""

    parts: frozenset[str]
    condition_labels: frozenset[str]


@dataclass(frozen=True)
class PetConsentFacts:
    """동의서를 조립하고 덮인 것을 계산하는 데 쓰는 아이의 사실."""

    pet_id: int
    name: str
    birth_date: date | None
    birth_year: int | None
    condition_labels: tuple[str, ...]      # 보호자에게 보이는 지병 이름(기타면 직접 적은 이름), 종류의 순서대로
    consent_on: date | None                # 미용 동의를 받은 날
    via_signature: bool                    # 그 동의가 서명으로 받은 것인가(아니면 손으로 적은 것)
    signed: tuple[SignedCover, ...]        # 받은 날부터의 서명들이 덮은 것
    passed_away: bool


@dataclass(frozen=True)
class DocumentPet:
    """동의서 한 장에서 아이 하나의 구역."""

    pet_id: int
    name: str
    condition_labels: tuple[str, ...]
    parts: tuple[str, ...]    # 이번에 읽고 서명할 토막(남은 것)
    full: bool                # 이번 서명이 전체 서명인가 — 그러면 받은 날을 찍는다
