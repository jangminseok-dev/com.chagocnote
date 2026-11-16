from datetime import date

from customer.domain.entities.consent import ConsentPolicy, PetConsentFacts, SignedCover
from customer.domain.services.consent_document import build_document, doc_digest, needed_parts

TODAY = date(2026, 11, 16)
POLICY = ConsentPolicy()
VERSIONS = {"basic": ("default", 1), "senior": ("default", 1), "condition": ("default", 1)}


def _pet(pet_id=1, name="콩이", birth_date=None, birth_year=None, labels=(), consent_on=None,
         via_signature=False, signed=(), passed_away=False) -> PetConsentFacts:
    return PetConsentFacts(
        pet_id=pet_id, name=name, birth_date=birth_date, birth_year=birth_year, condition_labels=tuple(labels),
        consent_on=consent_on, via_signature=via_signature, signed=tuple(signed), passed_away=passed_away)


def test_아홉_살은_basic_만_열_살은_senior_가_붙는다():
    assert needed_parts(_pet(birth_date=date(2016, 11, 17)), TODAY, POLICY) == ("basic",)      # 생일 하루 전
    assert needed_parts(_pet(birth_date=date(2016, 11, 16)), TODAY, POLICY) == ("basic", "senior")


def test_태어난_해만_알면_해의_차이로_본다():
    assert needed_parts(_pet(birth_year=2016), TODAY, POLICY) == ("basic", "senior")
    assert needed_parts(_pet(birth_year=2017), TODAY, POLICY) == ("basic",)


def test_지병이_있으면_condition_이_붙는다():
    assert needed_parts(_pet(labels=("심장",)), TODAY, POLICY) == ("basic", "condition")


def test_남은_토막이_없는_아이와_무지개다리_아이는_문서에서_빠진다():
    covered = _pet(pet_id=1, consent_on=date(2026, 11, 1), via_signature=True,
                   signed=[SignedCover(frozenset({"basic"}), frozenset())])
    gone = _pet(pet_id=2, passed_away=True)
    fresh = _pet(pet_id=3, name="보리", labels=("피부",))
    doc = build_document([covered, gone, fresh], TODAY, POLICY)
    assert [(p.pet_id, p.parts, p.full) for p in doc] == [(3, ("basic", "condition"), True)]


def test_바뀐_토막만_남으면_전체_서명이_아니다():
    pet = _pet(labels=("심장", "피부"), consent_on=date(2026, 11, 1), via_signature=True,
               signed=[SignedCover(frozenset({"basic", "condition"}), frozenset({"심장"}))])
    (only,) = build_document([pet], TODAY, POLICY)
    assert (only.parts, only.full, only.condition_labels) == (("condition",), False, ("심장", "피부"))


def test_지병이_하나에서_둘이_되면_지문이_다르다():
    one = build_document([_pet(labels=("심장",))], TODAY, POLICY)
    two = build_document([_pet(labels=("심장", "피부"))], TODAY, POLICY)
    assert doc_digest(one, VERSIONS) != doc_digest(two, VERSIONS)


def test_아이_이름이나_토막의_판이_바뀌면_지문이_다르다():
    doc = build_document([_pet(labels=("심장",))], TODAY, POLICY)
    renamed = build_document([_pet(name="콩", labels=("심장",))], TODAY, POLICY)
    assert doc_digest(doc, VERSIONS) != doc_digest(renamed, VERSIONS)
    assert doc_digest(doc, VERSIONS) != doc_digest(doc, {**VERSIONS, "condition": ("default", 2)})
    assert doc_digest(doc, VERSIONS) != doc_digest(doc, {**VERSIONS, "basic": ("shop", 1)})


def test_같은_사실이면_아이를_넣는_순서가_달라도_지문이_같다():
    a, b = _pet(pet_id=1), _pet(pet_id=2, name="보리", labels=("피부",))
    assert doc_digest(build_document([a, b], TODAY, POLICY), VERSIONS) == doc_digest(
        build_document([b, a], TODAY, POLICY), VERSIONS)


def test_쓰지_않는_토막의_판은_지문에_들지_않는다():
    doc = build_document([_pet()], TODAY, POLICY)   # basic 뿐
    assert doc_digest(doc, VERSIONS) == doc_digest(doc, {**VERSIONS, "senior": ("shop", 9)})
