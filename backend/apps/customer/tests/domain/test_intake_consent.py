"""문진표 끝의 동의서(⑪-C1b) — 답으로 붙는 토막과, 보호자가 연 뒤 매장의 글·기준이 바뀌었는지 보는 지문."""
from dataclasses import replace
from datetime import date

import pytest

from customer.domain.entities.consent import ConsentPolicy
from customer.domain.services.intake_consent import consent_parts, shown_conditions, texts_digest
from customer.domain.services.intake_rules import CleanAnswer
from customer.domain.value_objects.condition_entry import ConditionEntry

ON = date(2026, 11, 16)
POLICY = ConsentPolicy()       # 노령 10살

ANSWER = CleanAnswer(
    guardian_name="박새롬", guardian_phone="01099990000", pet_name="모카", species="dog", breed="푸들",
    sex="male", neutered=False, birth_date=None, birth_year=None, birth_unknown=True, weight_kg=None,
    no_known_conditions=True, conditions=(), dislikes=None, style=None, extras=(),
)


def parts(answer=ANSWER, policy=POLICY, for_all=False):
    return consent_parts(answer, on=ON, policy=policy, for_all=for_all)


@pytest.mark.parametrize(("change", "expected"), [
    ({}, ()),                                                                        # 노령도 지병도 아니다
    ({"birth_year": 2016, "birth_unknown": False}, ("basic", "senior")),            # 해의 차이 10살
    ({"birth_year": 2017, "birth_unknown": False}, ()),                              # 9살
    ({"birth_date": date(2016, 11, 16), "birth_unknown": False}, ("basic", "senior")),   # 생일 당일 10살
    ({"birth_date": date(2016, 11, 17), "birth_unknown": False}, ()),                # 하루 모자란 9살
    ({"no_known_conditions": False, "conditions": (ConditionEntry("heart_disease", None, None),)},
     ("basic", "condition")),
    ({"birth_year": 2010, "birth_unknown": False, "no_known_conditions": False,
      "conditions": (ConditionEntry("other", "눈물", None),)}, ("basic", "senior", "condition")),
])
def test_노령이거나_지병을_골랐을_때만_토막이_붙는다(change, expected):
    assert parts(replace(ANSWER, **change)) == expected


def test_매장의_노령_나이를_따르고_모든_아이에게를_켜면_미용_안내만이라도_붙는다():
    eight = replace(ANSWER, birth_year=2018, birth_unknown=False)

    assert parts(eight) == ()
    assert parts(eight, policy=ConsentPolicy(senior_age=8)) == ("basic", "senior")
    assert parts(ANSWER, for_all=True) == ("basic",)


def test_다시_받기에서_나이도_지병도_적지_않았으면_토막이_없다():
    blank = replace(ANSWER, birth_unknown=False, no_known_conditions=None)

    assert parts(blank) == ()


def test_보인_지병_이름은_종류의_이름이거나_직접_적은_이름이다():
    answer = replace(ANSWER, no_known_conditions=False, conditions=(
        ConditionEntry("heart_disease", None, "약 먹어요"), ConditionEntry("other", "눈물 자국", None)))

    assert shown_conditions(answer, {"heart_disease": "심장 질환"}) == ("심장 질환", "눈물 자국")


def test_지문은_글의_판_노령_나이_모든_아이에게_중_하나만_바뀌어도_다르다():
    versions = {"basic": ("default", 1), "senior": ("default", 1), "condition": ("default", 1)}
    base = texts_digest(versions, POLICY, False)

    assert base == texts_digest(dict(versions), ConsentPolicy(), False)
    assert base != texts_digest({**versions, "senior": ("shop", 1)}, POLICY, False)
    assert base != texts_digest({**versions, "condition": ("default", 2)}, POLICY, False)
    assert base != texts_digest(versions, ConsentPolicy(senior_age=8), False)
    assert base != texts_digest(versions, POLICY, True)
    # 동의 기한·링크 기간은 보호자가 읽는 것이 아니다 — 지문에 들지 않는다.
    assert base == texts_digest(versions, ConsentPolicy(consent_days=30, link_days=3), False)
