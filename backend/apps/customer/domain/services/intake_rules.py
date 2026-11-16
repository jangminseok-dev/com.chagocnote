"""문진표 답의 검증(⑪ 설계 3.4). 순수 함수 — 오류 글에 보호자가 적은 글을 싣지 않는다.

켜진 칸은 필수이고(생일은 셋 중 하나, 몸무게는 둘 중 하나, 지병은 `없어요` 나 하나 이상) 매장이 끈 칸은 적어 보내도
버린다. 이미 있는 아이의 정보를 다시 받을 때(update)는 전부 선택이다 — 바뀐 것만 적는다.
빈칸을 지어내지 않는다: 끈 칸·`모르겠어요` 는 None 으로 남기고 등록할 때 사장에게 묻는다.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from customer.domain.entities.intake import NEW, UPDATE, IntakeQuestion
from customer.domain.errors import CustomerInputError
from customer.domain.services.pet_health import check_conditions
from customer.domain.services.phone_number import normalize_phone
from customer.domain.value_objects.condition_entry import ConditionEntry

OLDEST_BIRTH_YEAR = 1990
SPECIES = ("dog", "cat")
SEXES = ("female", "male")


@dataclass(frozen=True)
class IntakeEntry:
    """보호자가 낸 것 그대로. 문자열은 앞뒤 공백을 없앴고 빈 값은 None 이다(스키마가 바꿔 넣는다)."""

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
    weight_unknown: bool
    no_known_conditions: bool | None
    conditions: tuple[ConditionEntry, ...]
    dislikes: str | None
    style: str | None
    extras: tuple[tuple[int, str], ...]      # (질문 ID, 답)
    privacy_agreed: bool


@dataclass(frozen=True)
class CleanAnswer:
    """저장할 답. 끈 칸·모르는 값·묻지 않은 칸은 None 이다."""

    guardian_name: str | None
    guardian_phone: str | None               # 숫자만
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
    conditions: tuple[ConditionEntry, ...]
    dislikes: str | None
    style: str | None
    extras: tuple[tuple[int, str], ...]


def _missing(what: str) -> CustomerInputError:
    return CustomerInputError(f"{what}을(를) 적어 주세요.")


def clean_entry(
    entry: IntakeEntry, *, mode: str, hidden: frozenset[str], questions: list[IntakeQuestion],
    known_codes: frozenset[str], today: date, first: bool,
) -> CleanAnswer:
    """first 는 이 링크의 첫 답인가 — 새 손님의 보호자 칸은 첫 답에서만 묻는다(둘째부터는 그 보호자다)."""
    if entry.privacy_agreed is not True:
        raise CustomerInputError("개인정보 수집·이용 안내에 동의해 주세요.")
    # 공백만 든 글은 적지 않은 것이다(스키마도 그렇게 바꿔 넣지만 여기서 한 번 더 본다).
    entry = replace(entry, **{
        name: (getattr(entry, name) or "").strip() or None
        for name in ("guardian_name", "guardian_phone", "pet_name", "breed", "dislikes", "style")
    })
    required = mode != UPDATE
    shown = lambda code: code not in hidden      # noqa: E731

    guardian_name = guardian_phone = None
    if mode == NEW and first:
        if not entry.guardian_name:
            raise _missing("보호자 이름")
        if not entry.guardian_phone:
            raise _missing("전화번호")
        guardian_name, guardian_phone = entry.guardian_name, normalize_phone(entry.guardian_phone)
    if required and not entry.pet_name:
        raise _missing("아이 이름")

    species = entry.species if shown("species") else None
    if species is None and required and shown("species"):
        raise _missing("종")
    if species is not None and species not in SPECIES:
        raise CustomerInputError("종을 다시 골라 주세요.")
    breed = entry.breed if shown("breed") else None
    if breed is None and required and shown("breed"):
        raise _missing("품종")
    sex = entry.sex if shown("sex") else None
    if sex is None and required and shown("sex"):
        raise _missing("성별")
    if sex is not None and sex not in SEXES:
        raise CustomerInputError("성별을 다시 골라 주세요.")
    neutered = entry.neutered if shown("neutered") else None
    if neutered is None and required and shown("neutered"):
        raise _missing("중성화 여부")

    birth_date = birth_year = None
    birth_unknown = False
    if shown("birth"):
        given = sum((entry.birth_date is not None, entry.birth_year is not None, entry.birth_unknown))
        if given > 1 or (required and given == 0):
            raise CustomerInputError("생일, 태어난 해, 몰라요 가운데 하나를 골라 주세요.")
        if entry.birth_date is not None and not date(OLDEST_BIRTH_YEAR, 1, 1) <= entry.birth_date <= today:
            raise CustomerInputError("생일을 다시 확인해 주세요.")
        if entry.birth_year is not None and not OLDEST_BIRTH_YEAR <= entry.birth_year <= today.year:
            raise CustomerInputError("태어난 해를 다시 확인해 주세요.")
        birth_date, birth_year, birth_unknown = entry.birth_date, entry.birth_year, entry.birth_unknown

    weight = None
    if shown("weight"):
        if entry.weight_kg is not None and entry.weight_unknown:
            raise CustomerInputError("몸무게와 모르겠어요 가운데 하나만 골라 주세요.")
        if required and entry.weight_kg is None and not entry.weight_unknown:
            raise _missing("몸무게")
        if entry.weight_kg is not None and entry.weight_kg <= 0:
            raise CustomerInputError("몸무게를 다시 확인해 주세요.")
        weight = entry.weight_kg

    # 지병은 끌 수 없다 — 동의서의 토막이 이것으로 정해진다. 다시 받기에서 아무것도 고르지 않으면 "답하지 않음"이다.
    none, conditions = entry.no_known_conditions, entry.conditions
    if required and none is None:
        raise CustomerInputError("지병을 고르거나 없어요를 골라 주세요.")
    if none is None and conditions:
        none = False
    if none is not None:
        if none == bool(conditions):
            raise CustomerInputError("지병을 고르거나 없어요를 골라 주세요.")
        check_conditions(conditions, none, known_codes)      # 종류 코드·기타의 이름 — 등록 화면과 같은 규칙

    live = {question.id: question for question in questions}
    # 지운 질문의 답은 그 답만 버린다 — 보호자가 연 뒤 매장이 질문을 고쳤을 수 있다.
    extras = tuple((qid, body) for qid, body in entry.extras if qid in live and body.strip())
    if len({qid for qid, _ in extras}) != len(extras):
        raise CustomerInputError("같은 질문에 답이 둘입니다.")
    if required:
        answered = {qid for qid, _ in extras}
        if any(question.required and question.id not in answered for question in questions):
            raise CustomerInputError("꼭 답해야 하는 질문이 남아 있습니다.")

    return CleanAnswer(
        guardian_name=guardian_name, guardian_phone=guardian_phone, pet_name=entry.pet_name or None,
        species=species, breed=breed, sex=sex, neutered=neutered, birth_date=birth_date, birth_year=birth_year,
        birth_unknown=birth_unknown, weight_kg=weight, no_known_conditions=none,
        conditions=conditions if none is False else (),
        dislikes=entry.dislikes if shown("dislikes") else None, style=entry.style if shown("style") else None,
        extras=extras,
    )
