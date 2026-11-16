"""예약 앞에서 확인할 것의 판정 — 날짜의 끝과 항목의 순서(③-B 설계 3.1). 기준일은 2026-11-14."""
from datetime import date

import pytest

from visit.domain.services.visit_checks import COUNTED, age_on, checks_for
from visit.domain.value_objects.check_facts import CautionMark, CheckSubject, ConsentCoverFact, PetFacts

ON = date(2026, 11, 14)
RECENT = date(2026, 10, 1)   # 44일 전 — 오랜만이 아니다


def pet(birth_date=None, birth_year=2021, conditions=(), consent_on=None, passed_away=False) -> PetFacts:
    return PetFacts(birth_date=birth_date, birth_year=birth_year, conditions=tuple(conditions),
                    consent_on=consent_on, passed_away=passed_away)


def subject(pet_=None, on=ON, caution=None, no_show=0, last=RECENT) -> CheckSubject:
    return CheckSubject(on=on, pet=pet_, caution=caution, no_show_count=no_show, last_completed_on=last)


def codes(found) -> list[str]:
    return [check.code for check in found]


def one(found, code):
    return next(check for check in found if check.code == code)


@pytest.mark.parametrize("birth_date,birth_year,on,age", [
    (date(2016, 11, 14), None, date(2026, 11, 14), 10),   # 열 번째 생일 당일
    (date(2016, 11, 15), None, date(2026, 11, 14), 9),    # 하루 전
    (date(2016, 11, 13), None, date(2026, 11, 14), 10),
    (date(2016, 2, 29), None, date(2026, 2, 28), 9),      # 윤일생 — 2월 28일에는 아직
    (date(2016, 2, 29), None, date(2026, 3, 1), 10),
    (None, 2016, date(2026, 1, 1), 10),                   # 연도만 알면 그 해 − 출생 연도
    (None, 2017, date(2026, 12, 31), 9),
    (None, None, date(2026, 11, 14), None),
])
def test_그날의_나이(birth_date, birth_year, on, age):
    assert age_on(birth_date, birth_year, on) == age


def test_확인할_것이_없는_평범한_방문은_빈_목록이다():
    assert checks_for(subject(pet())) == []


def test_순서는_주의_노쇼_첫_방문_동의_지병이고_보호자_항목이_앞이다():
    found = checks_for(subject(
        pet(birth_year=2010, conditions=[("심장 질환", "약 복용 중"), ("눈물 자국", None)]),
        caution=CautionMark("입질", date(2027, 1, 1)), no_show=2, last=None,
    ))
    assert codes(found) == ["caution", "no_show", "first_visit", "consent", "conditions"]
    assert [c.scope for c in found] == ["customer", "customer", "pet", "pet", "pet"]
    assert one(found, "caution").detail == {"reason": "입질", "until": date(2027, 1, 1)}
    assert one(found, "no_show").detail == {"count": 2}
    assert one(found, "first_visit").detail == {}
    assert one(found, "consent").detail == {
        "reasons": ["senior", "conditions"], "state": "missing", "received_on": None,
    }
    assert one(found, "conditions").detail == {"items": [
        {"label": "심장 질환", "note": "약 복용 중"}, {"label": "눈물 자국", "note": None},
    ]}


@pytest.mark.parametrize("birth_date,birth_year,senior", [
    (date(2016, 11, 14), None, True),    # 방문 날이 열 번째 생일
    (date(2016, 11, 15), None, False),
    (None, 2016, True),
    (None, 2017, False),
    (None, None, False),                 # 나이를 모르면 노령이 아니다
])
def test_열_살부터_노령이고_동의를_받게_한다(birth_date, birth_year, senior):
    found = checks_for(subject(pet(birth_date=birth_date, birth_year=birth_year)))
    assert ("consent" in codes(found)) is senior
    if senior:
        assert one(found, "consent").detail["reasons"] == ["senior"]


def test_지금은_아홉_살이어도_예약일에_열_살이면_뜬다():
    young = pet(birth_date=date(2016, 12, 1), birth_year=None)
    assert "consent" not in codes(checks_for(subject(young, on=date(2026, 11, 30))))
    assert "consent" in codes(checks_for(subject(young, on=date(2026, 12, 1))))


@pytest.mark.parametrize("consent_on,state", [
    (date(2025, 11, 14), None),          # 365일째 — 유효
    (date(2025, 11, 13), "expired"),     # 366일째
    (date(2026, 11, 14), None),          # 그날 받음
    (date(2026, 11, 20), None),          # 방문 날보다 뒤에 받음(지난 채 남은 예약) — 유효
    (date(2020, 1, 1), "expired"),
    (None, "missing"),
])
def test_동의는_받은_날로부터_365일째까지_유효하다(consent_on, state):
    found = checks_for(subject(pet(conditions=[("알레르기", None)], consent_on=consent_on)))
    if state is None:
        assert codes(found) == ["conditions"]   # 동의가 유효해도 지병은 정보로 뜬다
    else:
        detail = one(found, "consent").detail
        assert (detail["state"], detail["received_on"], detail["reasons"]) == (state, consent_on, ["conditions"])


def test_노령도_지병도_아니면_동의가_없어도_뜨지_않는다():
    assert checks_for(subject(pet(consent_on=None))) == []


@pytest.mark.parametrize("last,days", [
    (date(2026, 5, 18), None),    # 180일 — 뜨지 않는다
    (date(2026, 5, 17), 181),     # 181일
    (date(2025, 1, 1), 682),
    (date(2026, 11, 14), None),   # 같은 날 앞서 다녀감
])
def test_마지막_완료_방문이_180일을_넘으면_오랜만이다(last, days):
    found = checks_for(subject(pet(), last=last))
    if days is None:
        assert found == []
    else:
        assert codes(found) == ["long_absence"]
        assert one(found, "long_absence").detail == {"days": days, "last_visit_on": last}


def test_이력이_없으면_첫_방문뿐이고_오랜만은_함께_뜨지_않는다():
    assert codes(checks_for(subject(pet(), last=None))) == ["first_visit"]


def test_무지개다리를_건넌_아이의_방문에는_아이_쪽_항목이_없다():
    gone = pet(birth_year=2005, conditions=[("심장 질환", None)], passed_away=True)
    found = checks_for(subject(gone, no_show=1, last=None))
    assert codes(found) == ["no_show"]


def test_보호자만의_방문에는_보호자_항목만_있다():
    found = checks_for(subject(None, caution=CautionMark("노쇼 2번", date(2026, 11, 14)), no_show=3, last=None))
    assert codes(found) == ["caution", "no_show"]


def test_노쇼가_없으면_노쇼_항목이_없다():
    assert "no_show" not in codes(checks_for(subject(pet(), no_show=0)))


def test_하루_목록의_수에는_지병을_세지_않는다():
    assert COUNTED == {"caution", "no_show", "first_visit", "consent", "long_absence"}


# --- 서명으로 받은 동의(⑪) — 바뀐 토막만 다시 --------------------------------------------------------------------

def _signed(senior=False, labels=()) -> ConsentCoverFact:
    return ConsentCoverFact(senior=senior, condition_labels=frozenset(labels))


def test_서명으로_받은_동의는_노령이_되면_partial_senior_다():
    old = PetFacts(birth_date=None, birth_year=2016, conditions=(), consent_on=date(2026, 3, 2), passed_away=False,
                   consent_cover=_signed())
    detail = one(checks_for(subject(old)), "consent").detail
    assert detail == {"reasons": ["senior"], "state": "partial", "received_on": date(2026, 3, 2), "parts": ["senior"]}


def test_서명이_덮지_않은_지병이_있으면_partial_condition_이다():
    sick = PetFacts(birth_date=None, birth_year=2021, conditions=(("심장 질환", None), ("알레르기", None)),
                    consent_on=date(2026, 3, 2), passed_away=False, consent_cover=_signed(labels=["심장 질환"]))
    detail = one(checks_for(subject(sick)), "consent").detail
    assert (detail["state"], detail["parts"], detail["reasons"]) == ("partial", ["condition"], ["conditions"])


def test_서명이_노령과_지병을_다_덮으면_뜨지_않는다():
    covered = PetFacts(birth_date=None, birth_year=2016, conditions=(("심장 질환", None),),
                       consent_on=date(2026, 3, 2), passed_away=False,
                       consent_cover=_signed(senior=True, labels=["심장 질환", "피부"]))
    assert "consent" not in codes(checks_for(subject(covered)))


def test_서명으로_받았어도_기한이_지나면_expired_이고_토막을_가르지_않는다():
    late = PetFacts(birth_date=None, birth_year=2016, conditions=(), consent_on=date(2025, 11, 13), passed_away=False,
                    consent_cover=_signed())
    detail = one(checks_for(subject(late)), "consent").detail
    assert detail["state"] == "expired" and "parts" not in detail


def test_손으로_적은_동의는_노령이_돼도_뜨지_않는다():
    # ③-B 의 동작 그대로다 — 손 표시는 무엇을 읽었는지 기록이 없어 토막을 가르지 않는다.
    old = PetFacts(birth_date=None, birth_year=2016, conditions=(), consent_on=date(2026, 3, 2), passed_away=False)
    assert "consent" not in codes(checks_for(subject(old)))


def test_보낸_날이_있으면_detail_에_실리고_없으면_칸이_없다():
    waiting = PetFacts(birth_date=None, birth_year=2016, conditions=(), consent_on=None, passed_away=False,
                       consent_form_sent_on=date(2026, 11, 13))
    assert one(checks_for(subject(waiting)), "consent").detail["form_sent_on"] == date(2026, 11, 13)
    plain = PetFacts(birth_date=None, birth_year=2016, conditions=(), consent_on=None, passed_away=False)
    assert "form_sent_on" not in one(checks_for(subject(plain)), "consent").detail


# --- 매장이 바꾼 기준값(⑪-B) ---------------------------------------------------------------------------------------

def test_매장이_노령_나이를_여덟_살로_낮추면_여덟_살부터_동의를_받게_한다():
    eight = pet(birth_year=2018)

    assert "consent" not in codes(checks_for(subject(eight)))
    lowered = CheckSubject(on=ON, pet=eight, caution=None, no_show_count=0, last_completed_on=RECENT, senior_age=8)
    assert one(checks_for(lowered), "consent").detail["reasons"] == ["senior"]


def test_매장이_노령_나이를_높이면_열_살이어도_뜨지_않는다():
    raised = CheckSubject(on=ON, pet=pet(birth_year=2016), caution=None, no_show_count=0,
                          last_completed_on=RECENT, senior_age=12)
    assert "consent" not in codes(checks_for(raised))


def test_매장이_동의_기한을_30일로_줄이면_31일_지난_동의는_expired_다():
    senior = lambda consent_on: pet(birth_year=2010, consent_on=consent_on)      # noqa: E731
    short = lambda p: CheckSubject(on=ON, pet=p, caution=None, no_show_count=0,   # noqa: E731
                                   last_completed_on=RECENT, consent_days=30)

    assert "consent" not in codes(checks_for(short(senior(date(2026, 10, 15)))))            # 30일째
    assert one(checks_for(short(senior(date(2026, 10, 14)))), "consent").detail["state"] == "expired"
    assert "consent" not in codes(checks_for(subject(senior(date(2026, 10, 14)))))          # 기본 365일이면 유효


def test_서명으로_받은_동의는_낮춘_노령_나이에_닿으면_partial_senior_다():
    signed = PetFacts(birth_date=None, birth_year=2018, conditions=(), consent_on=date(2026, 6, 1), passed_away=False,
                      consent_cover=ConsentCoverFact(senior=False, condition_labels=frozenset()))
    lowered = CheckSubject(on=ON, pet=signed, caution=None, no_show_count=0, last_completed_on=RECENT, senior_age=8)

    detail = one(checks_for(lowered), "consent").detail
    assert (detail["state"], detail["parts"], detail["received_on"]) == ("partial", ["senior"], date(2026, 6, 1))


# --- 기한보다 먼 예약(최종 검토) — 지금 받을 수 있는 동의로 본다 -----------------------------------------------------

def test_기한보다_먼_예약은_오늘에_기한을_더한_날로_동의를_본다():
    # 기한 30일, 예약은 40일 뒤. 오늘 받은 동의는 40일 뒤에는 지났지만 지금 더 받을 길이 없다.
    today = date(2026, 10, 5)
    far = lambda consent_on, now: CheckSubject(                                    # noqa: E731
        on=ON, pet=pet(birth_year=2010, consent_on=consent_on), caution=None, no_show_count=0,
        last_completed_on=RECENT, consent_days=30, today=now)

    assert one(checks_for(far(None, today)), "consent").detail["state"] == "missing"
    assert "consent" not in codes(checks_for(far(today, today)))                   # 오늘 받았으면 지금은 더 받을 것이 없다
    near = date(2026, 10, 16)                                                      # 예약 29일 전 — 이제 예약 날로 본다
    assert one(checks_for(far(today, near)), "consent").detail["state"] == "expired"
