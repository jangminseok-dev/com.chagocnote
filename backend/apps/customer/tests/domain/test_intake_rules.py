"""문진표 답의 검증(⑪ 설계 3.4) — 켜진 칸은 필수, 끈 칸은 버리고, 다시 받기는 전부 선택."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from customer.domain.entities.intake import ADD_PET, NEW, UPDATE, IntakeQuestion
from customer.domain.errors import CustomerInputError
from customer.domain.services.intake_rules import IntakeEntry, clean_entry
from customer.domain.value_objects.condition_entry import ConditionEntry

TODAY = date(2026, 11, 16)
CODES = frozenset({"heart_disease", "allergy", "other"})
QUESTIONS = [IntakeQuestion(id=7, label="산책은 얼마나 하나요?", required=True),
             IntakeQuestion(id=8, label="간식은요?", required=False)]

FULL = IntakeEntry(
    guardian_name="김민지", guardian_phone="010-1234-5678", pet_name="콩이", species="dog", breed="말티즈",
    sex="female", neutered=True, birth_date=None, birth_year=2021, birth_unknown=False,
    weight_kg=Decimal("3.2"), weight_unknown=False, no_known_conditions=True, conditions=(),
    dislikes="발 만지기", style="짧게", extras=((7, "하루 한 번"),), privacy_agreed=True,
)


def clean(entry=FULL, mode=NEW, hidden=(), questions=QUESTIONS, first=True):
    return clean_entry(entry, mode=mode, hidden=frozenset(hidden), questions=questions, known_codes=CODES,
                       today=TODAY, first=first)


def test_다_적은_답은_그대로_받고_번호는_숫자만_남긴다():
    got = clean()

    assert (got.guardian_name, got.guardian_phone, got.pet_name) == ("김민지", "01012345678", "콩이")
    assert (got.species, got.breed, got.sex, got.neutered, got.birth_year, got.weight_kg) == (
        "dog", "말티즈", "female", True, 2021, Decimal("3.2"))
    assert (got.no_known_conditions, got.conditions, got.extras) == (True, (), ((7, "하루 한 번"),))


@pytest.mark.parametrize("change", [
    {"privacy_agreed": False},
    {"guardian_name": " "}, {"guardian_phone": "12345"}, {"pet_name": ""},
    {"species": None}, {"species": "bird"}, {"breed": None}, {"sex": None}, {"neutered": None},
    {"birth_year": None},                                             # 생일·태어난 해·몰라요 가운데 하나
    {"birth_date": date(2021, 1, 1)},                                 # 둘을 함께
    {"birth_year": 2027}, {"birth_year": None, "birth_date": date(2026, 11, 17)},
    {"weight_kg": None}, {"weight_kg": Decimal("0")},
    {"no_known_conditions": False},                                   # 없어요도 아니고 고른 것도 없다
    {"conditions": (ConditionEntry("heart_disease", None, None),)},   # 없어요인데 골랐다
    {"no_known_conditions": False, "conditions": (ConditionEntry("flu", None, None),)},
    {"extras": ()},                                                   # 필수 질문의 답이 없다
    {"extras": ((7, "  "),)},
])
def test_켜진_칸이_비었거나_틀리면_받지_않는다(change):
    with pytest.raises(CustomerInputError):
        clean(replace(FULL, **change))


def test_몰라요와_모르겠어요는_빈_값으로_받는다():
    got = clean(replace(FULL, birth_year=None, birth_unknown=True, weight_kg=None, weight_unknown=True))
    assert (got.birth_date, got.birth_year, got.birth_unknown, got.weight_kg) == (None, None, True, None)


def test_지병을_고르면_한_줄씩_함께_받는다():
    got = clean(replace(FULL, no_known_conditions=False, conditions=(
        ConditionEntry("heart_disease", None, "약 복용 중"), ConditionEntry("other", "슬개골", None))))
    assert [(c.type_code, c.custom_label, c.note) for c in got.conditions] == [
        ("heart_disease", None, "약 복용 중"), ("other", "슬개골", None)]


def test_매장이_끈_칸은_비어_있어도_되고_적어_보내도_버린다():
    hidden = ("species", "breed", "sex", "neutered", "birth", "weight", "dislikes", "style")
    bare = replace(FULL, species=None, breed=None, sex=None, neutered=None, birth_year=None, weight_kg=None,
                   dislikes=None, style=None)

    for entry in (bare, FULL):
        got = clean(entry, hidden=hidden)
        assert (got.species, got.breed, got.sex, got.neutered, got.birth_year, got.weight_kg, got.dislikes,
                got.style) == (None,) * 8
        assert got.pet_name == "콩이"


def test_지운_질문의_답은_그_답만_버린다():
    got = clean(replace(FULL, extras=((7, "하루 한 번"), (99, "지운 질문의 답"))))
    assert got.extras == ((7, "하루 한 번"),)


def test_새_아이와_둘째_답에는_보호자_칸을_묻지_않는다():
    bare = replace(FULL, guardian_name=None, guardian_phone=None)
    assert clean(bare, mode=ADD_PET).guardian_name is None
    assert clean(bare, first=False).guardian_phone is None
    # 적어 보내도 쓰지 않는다 — 첫 답의 보호자다.
    assert clean(FULL, first=False).guardian_name is None


def test_다시_받기는_전부_선택이고_적은_것만_남는다():
    nothing = IntakeEntry(
        guardian_name=None, guardian_phone=None, pet_name=None, species=None, breed=None, sex=None, neutered=None,
        birth_date=None, birth_year=None, birth_unknown=False, weight_kg=None, weight_unknown=False,
        no_known_conditions=None, conditions=(), dislikes=None, style=None, extras=(), privacy_agreed=True)

    got = clean(nothing, mode=UPDATE)
    assert (got.pet_name, got.weight_kg, got.no_known_conditions, got.conditions) == (None, None, None, ())
    only_weight = clean(replace(nothing, weight_kg=Decimal("4.1")), mode=UPDATE)
    assert only_weight.weight_kg == Decimal("4.1")
    with pytest.raises(CustomerInputError):
        clean(replace(nothing, privacy_agreed=False), mode=UPDATE)
    with pytest.raises(CustomerInputError):
        clean(replace(nothing, species="bird"), mode=UPDATE)


def test_오류_글에_적은_글이_들어가지_않는다():
    with pytest.raises(CustomerInputError) as caught:
        clean(replace(FULL, guardian_phone="비밀번호12345"))
    assert "비밀" not in str(caught.value) and "12345" not in str(caught.value)
