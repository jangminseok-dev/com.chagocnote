from datetime import date, timedelta

from customer.domain.entities.consent import ConsentPolicy, PetConsentFacts, SignedCover
from customer.domain.services.consent_coverage import uncovered

TODAY = date(2026, 11, 16)
POLICY = ConsentPolicy()
SIGNED_ON = date(2026, 3, 2)


def _pet(birth_date=None, labels=(), consent_on=None, via_signature=False, signed=()) -> PetConsentFacts:
    return PetConsentFacts(
        pet_id=1, name="콩이", birth_date=birth_date, birth_year=None, condition_labels=tuple(labels),
        consent_on=consent_on, via_signature=via_signature, signed=tuple(signed), passed_away=False)


def _cover(*parts, labels=()) -> SignedCover:
    return SignedCover(frozenset(parts), frozenset(labels))


def test_받은_날이_없으면_필요한_토막_전부이고_전체_서명이다():
    assert uncovered(_pet(labels=("심장",)), TODAY, POLICY) == (("basic", "condition"), True)


def test_삼백육십오일째는_덮이고_삼백육십육일째는_전부_다시다():
    pet = _pet(consent_on=SIGNED_ON, via_signature=True, signed=[_cover("basic")])
    assert uncovered(pet, SIGNED_ON + timedelta(days=365), POLICY) == ((), False)
    assert uncovered(pet, SIGNED_ON + timedelta(days=366), POLICY) == (("basic",), True)


def test_서명_뒤에_노령이_되면_senior_만_남는다():
    pet = _pet(birth_date=date(2016, 6, 1), consent_on=SIGNED_ON, via_signature=True, signed=[_cover("basic")])
    assert uncovered(pet, TODAY, POLICY) == (("senior",), False)


def test_서명_뒤에_지병이_더해지면_condition_만_남는다():
    pet = _pet(labels=("심장", "피부"), consent_on=SIGNED_ON, via_signature=True,
               signed=[_cover("basic", "condition", labels=("심장",))])
    assert uncovered(pet, TODAY, POLICY) == (("condition",), False)


def test_더해진_지병을_덮는_부분_서명이_있으면_남은_것이_없다():
    pet = _pet(labels=("심장", "피부"), consent_on=SIGNED_ON, via_signature=True,
               signed=[_cover("basic", "condition", labels=("심장",)), _cover("condition", labels=("심장", "피부"))])
    assert uncovered(pet, TODAY, POLICY) == ((), False)


def test_지병을_빼거나_메모만_고친_것은_남기지_않는다():
    pet = _pet(labels=("심장",), consent_on=SIGNED_ON, via_signature=True,
               signed=[_cover("basic", "condition", labels=("심장", "피부"))])
    assert uncovered(pet, TODAY, POLICY) == ((), False)


def test_지병이_없던_아이에게_처음_생기면_condition_이_남는다():
    pet = _pet(labels=("심장",), consent_on=SIGNED_ON, via_signature=True, signed=[_cover("basic")])
    assert uncovered(pet, TODAY, POLICY) == (("condition",), False)


def test_손으로_적은_동의는_토막을_가르지_않는다():
    # ③-B 의 지금 동작 그대로다 — 손 표시는 무엇을 읽었는지 기록이 없다. 지병이 늘면 수정 유스케이스가 받은 날을 지운다.
    pet = _pet(birth_date=date(2016, 6, 1), labels=("심장",), consent_on=SIGNED_ON)
    assert uncovered(pet, TODAY, POLICY) == ((), False)


def test_기준값을_바꾸면_따라간다():
    policy = ConsentPolicy(senior_age=8, consent_days=180)
    young = _pet(birth_date=date(2018, 6, 1), consent_on=date(2026, 9, 1), via_signature=True, signed=[_cover("basic")])
    assert uncovered(young, TODAY, policy) == (("senior",), False)
    assert uncovered(young, date(2026, 9, 1) + timedelta(days=181), policy) == (("basic", "senior"), True)
