"""서류 설정의 규칙(⑪-B). 순수 함수 — 오류 글에 매장이 적은 글을 싣지 않는다."""
from __future__ import annotations

import re

from customer.domain.errors import CustomerInputError
from customer.domain.value_objects.form_settings import FormSettings

LINK_DAYS = (1, 30)
SENIOR_AGE = (5, 20)
CONSENT_DAYS = (30, 1095)
TEMPLATE_MAX = 500
INTAKE_KEEP_DAYS = (7, 90)
# 문진표에서 매장이 끌 수 있는 칸. 보호자·아이 이름·지병·안내는 끌 수 없다 — 누구의 답인지, 어떤 동의가 필요한지가
# 여기서 정해진다.
INTAKE_HIDEABLE = ("species", "breed", "sex", "neutered", "birth", "weight", "dislikes", "style")

# 보내는 글에 넣을 수 있는 자리. 채우는 쪽은 visit 의 묶음 조립이다.
RESERVATION_SLOTS = frozenset({"{매장}", "{아이}", "{날짜}", "{시간}", "{메뉴}"})
CONSENT_SLOTS = frozenset({"{매장}", "{아이}", "{링크}"})
LINK_SLOT = "{링크}"

# 값이 빈 자리만 든 줄은 조립할 때 빠진다 — 메뉴가 없는 예약에 빈 줄이 나가지 않는다.
DEFAULT_RESERVATION_TEXT = "[{매장}] 예약이 접수됐어요.\n{날짜} {시간}\n{아이}\n{메뉴}"
DEFAULT_CONSENT_TEXT = "미용 전에 동의서를 읽고 서명해 주세요.\n{링크}"

_SLOT = re.compile(r"\{[^{}\s]*\}")


def _check_range(value: int, bounds: tuple[int, int], what: str) -> None:
    low, high = bounds
    if not low <= value <= high:
        raise CustomerInputError(f"{what}은(는) {low}부터 {high}까지 정할 수 있습니다.")


def _check_template(text: str | None, slots: frozenset[str], what: str) -> None:
    if text is None:
        return
    if not text.strip():
        raise CustomerInputError(f"{what}을(를) 비워 둘 수 없습니다. 기본 글로 되돌려 주세요.")
    if len(text) > TEMPLATE_MAX:
        raise CustomerInputError(f"{what}은(는) {TEMPLATE_MAX}자까지 적을 수 있습니다.")
    if any(slot not in slots for slot in _SLOT.findall(text)):
        raise CustomerInputError(f"{what}에 쓸 수 없는 자리가 있습니다.")


def check_form_settings(settings: FormSettings) -> None:
    _check_range(settings.link_days, LINK_DAYS, "링크를 열 수 있는 기간")
    _check_range(settings.senior_age, SENIOR_AGE, "노령으로 보는 나이")
    _check_range(settings.consent_days, CONSENT_DAYS, "동의를 다시 받는 기간")
    _check_template(settings.reservation_text, RESERVATION_SLOTS, "예약 안내 글")
    _check_template(settings.consent_text, CONSENT_SLOTS, "동의서를 보내는 글")
    if settings.consent_text is not None and LINK_SLOT not in settings.consent_text:
        raise CustomerInputError("동의서를 보내는 글에는 {링크} 자리가 있어야 합니다.")
    _check_range(settings.intake_keep_days, INTAKE_KEEP_DAYS, "확인하지 않은 문진표를 지우는 때")
    hidden = settings.intake_hidden
    if len(set(hidden)) != len(hidden) or any(code not in INTAKE_HIDEABLE for code in hidden):
        raise CustomerInputError("문진표에서 끌 수 없는 칸이 있습니다.")
