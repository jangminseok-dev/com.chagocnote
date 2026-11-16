"""서류 설정의 값과 규칙(⑪-B) — 범위, 보내는 글의 템플릿."""
from dataclasses import replace

import pytest

from customer.domain.errors import CustomerInputError
from customer.domain.services.form_settings_rules import (
    DEFAULT_CONSENT_TEXT, DEFAULT_RESERVATION_TEXT, check_form_settings,
)
from customer.domain.value_objects.form_settings import DEFAULT_FORM_SETTINGS


def test_기본값은_14일_10살_365일이고_글은_기본_글이다():
    s = DEFAULT_FORM_SETTINGS
    assert (s.link_days, s.senior_age, s.consent_days, s.reservation_text, s.consent_text) == (14, 10, 365, None, None)
    assert (s.policy.link_days, s.policy.senior_age, s.policy.consent_days) == (14, 10, 365)
    check_form_settings(s)


def test_기본_글은_자기_규칙을_지킨다():
    check_form_settings(replace(
        DEFAULT_FORM_SETTINGS, reservation_text=DEFAULT_RESERVATION_TEXT, consent_text=DEFAULT_CONSENT_TEXT))
    assert "{링크}" in DEFAULT_CONSENT_TEXT


@pytest.mark.parametrize("change", [
    {"link_days": 1}, {"link_days": 30}, {"senior_age": 5}, {"senior_age": 20},
    {"consent_days": 30}, {"consent_days": 1095},
    {"reservation_text": "예약됐어요 {날짜} {시간}"}, {"consent_text": "{매장}\n{링크}"},
    {"reservation_text": "가" * 500}, {"reservation_text": "중괄호 { 하나는 글자다"},
])
def test_범위_안의_값과_맞는_글은_받는다(change):
    check_form_settings(replace(DEFAULT_FORM_SETTINGS, **change))


@pytest.mark.parametrize("change", [
    {"link_days": 0}, {"link_days": 31}, {"senior_age": 4}, {"senior_age": 21},
    {"consent_days": 29}, {"consent_days": 1096},
    {"reservation_text": ""}, {"reservation_text": "  \n "}, {"reservation_text": "가" * 501},
    {"reservation_text": "{이름} 님 예약"},             # 모르는 자리
    {"reservation_text": "예약 {링크}"},                # 예약 안내에는 링크가 없다 — 빈칸으로 나간다
    {"consent_text": "동의서를 읽어 주세요"},            # 링크가 없으면 보호자가 열 수 없다
    {"consent_text": "{날짜} {링크}"},                  # 동의서 글에는 날짜가 없다
])
def test_범위_밖의_값과_빈칸이_나갈_글은_받지_않는다(change):
    with pytest.raises(CustomerInputError):
        check_form_settings(replace(DEFAULT_FORM_SETTINGS, **change))


def test_오류_글에_매장이_적은_글이_들어가지_않는다():
    with pytest.raises(CustomerInputError) as caught:
        check_form_settings(replace(DEFAULT_FORM_SETTINGS, reservation_text="비밀 글 {이름}"))
    assert "비밀" not in str(caught.value)
