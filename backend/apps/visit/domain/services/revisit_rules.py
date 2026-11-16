"""다시 올 때 설정의 규칙과 안내 글(⑬ 설계 3.3·3.7). 받은 글은 오류 글에 싣지 않는다."""
from __future__ import annotations

import unicodedata

from visit.domain.errors import VisitInputError
from visit.domain.value_objects.revisit_settings import (
    DEFAULT_CYCLE_WEEKS_RANGE,
    MESSAGE_MAX,
    MIN_GAP_DAYS_RANGE,
    SAMPLE_VISITS_RANGE,
    SOON_DAYS_RANGE,
    RevisitSettings,
)

# 처음 글 — 주기를 권고처럼 쓰지 않고 지난 사실만.
DEFAULT_REVISIT_MESSAGE = (
    "안녕하세요, {매장}예요.\n{아이}가 미용한 지 {주}주가 됐어요.\n편하신 날 알려 주시면 예약 잡아 드릴게요."
)
# 줄바꿈은 받는다(여러 줄 글이다). 그 밖의 제어·형식 문자(너비 없는 공백·방향 뒤집기)는 받지 않는다.
_HIDDEN = frozenset({"Cc", "Cf", "Zl", "Zp"})


def _between(value: int, bounds: tuple[int, int]) -> bool:
    return bounds[0] <= value <= bounds[1]


def check_revisit_settings(settings: RevisitSettings) -> None:
    ranges = (
        (settings.default_cycle_weeks, DEFAULT_CYCLE_WEEKS_RANGE),
        (settings.revisit_soon_days, SOON_DAYS_RANGE),
        (settings.cycle_sample_visits, SAMPLE_VISITS_RANGE),
        (settings.cycle_min_gap_days, MIN_GAP_DAYS_RANGE),
    )
    if not all(_between(value, bounds) for value, bounds in ranges):
        raise VisitInputError("다시 올 때 설정의 값이 고를 수 있는 범위 밖입니다.")
    message = settings.revisit_message
    if message is not None and (
        not message.strip() or len(message) > MESSAGE_MAX
        or any(unicodedata.category(ch) in _HIDDEN and ch != "\n" for ch in message)
    ):
        raise VisitInputError("안내 글은 비어 있지 않은 300자 이하의 글이어야 합니다.")


def fill_message(template: str | None, *, shop: str, pet: str, weeks: int) -> str:
    """템플릿(없으면 처음 글)에 매장 이름·아이 이름·지난 주 수를 넣는다. 모르는 자리는 그대로 둔다."""
    text = template or DEFAULT_REVISIT_MESSAGE
    return text.replace("{매장}", shop).replace("{아이}", pet).replace("{주}", str(weeks))
