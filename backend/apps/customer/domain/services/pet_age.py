"""반려동물 나이 — 생일·태어난 해·모름 중 하나만, 그리고 목록에 보여 줄 나이 표시."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from customer.domain.errors import CustomerInputError

_KST = timezone(timedelta(hours=9))   # 한국은 일광 절약 시간이 없다
_OLDEST_YEARS = 40


def seoul_today() -> date:
    """나이 계산의 '오늘'. 매장이 모두 한국에 있다(매장 시간대 기본값 Asia/Seoul)."""
    return datetime.now(_KST).date()


def check_birth(birth_date: date | None, birth_year: int | None, today: date) -> None:
    """생일과 태어난 해는 함께 보내지 않는다. 둘 다 없으면 '모름'이다."""
    if birth_date is not None and birth_year is not None:
        raise CustomerInputError("생일과 태어난 해 중 하나만 보내 주세요.")
    if birth_date is not None and not (today.year - _OLDEST_YEARS <= birth_date.year and birth_date <= today):
        raise CustomerInputError("생일이 올바르지 않습니다.")
    if birth_year is not None and not (today.year - _OLDEST_YEARS <= birth_year <= today.year):
        raise CustomerInputError("태어난 해가 올바르지 않습니다.")


def age_label(birth_date: date | None, birth_year: int | None, today: date) -> str:
    """생일이 있으면 만 나이(1살 전에는 개월), 태어난 해만 있으면 해의 차이, 없으면 '나이 모름'."""
    if birth_date is not None:
        months = (today.year - birth_date.year) * 12 + today.month - birth_date.month
        if today.day < birth_date.day:
            months -= 1
        return f"{months}개월" if months < 12 else f"{months // 12}살"
    if birth_year is not None:
        years = today.year - birth_year
        return "1살 미만" if years < 1 else f"{years}살"
    return "나이 모름"
