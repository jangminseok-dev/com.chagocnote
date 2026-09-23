"""카톡 예약 초안 — 보호자가 보낸 글에서 날짜·시각·메뉴·"누구" 낱말을 규칙으로 뽑는다(설계 7절).

외부 전송이 없다. 못 찾은 칸은 비우고, 두 가지로 읽히는 표현은 "짐작함"으로 표시한다 — 결과는 사람이 확인한 뒤
저장한다. 글과 낱말은 이 함수 밖에 남기지 않는다(로그·DB·오류 응답 금지, V9).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import Sequence

_WEEKDAYS = "월화수목금토일"
# 긴 상대 표현부터 본다 — "내일모레"는 모레다.
_RELATIVE = (("글피", 3), ("모레", 2), ("내일", 1), ("오늘", 0))
_WEEK_DAY = re.compile(r"(이번|다음) ?주 ?([월화수목금토일])요일")
_PLAIN_DAY = re.compile(r"([월화수목금토일])요일")
_MONTH_DAY = re.compile(r"(?<!\d)(\d{1,2}) ?월 ?(\d{1,2}) ?일(?!\d)")
_SLASH_DAY = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)")
_DAY_ONLY = re.compile(r"(?<!\d)(\d{1,2}) ?일(?!\d)")

# "2시간"의 "시"는 시각이 아니다 — 뒤에 "간"이 붙으면 건너뛴다.
_MARKED_TIME = re.compile(r"(오전|아침|오후|저녁|밤|낮) ?(\d{1,2}) ?시(?!간) ?(?:(반)|(\d{1,2}) ?분)?")
_CLOCK_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_HOUR_TIME = re.compile(r"(?<!\d)(\d{1,2}) ?시(?!간) ?(?:(반)|(\d{1,2}) ?분)?")
_AFTERNOON = ("오후", "저녁", "밤")
# 카톡 대화를 여러 줄 복사하면 줄마다 "[보낸 사람] [오후 2:31]" 머리말이 붙는다 — 그 시각은 예약 시각이 아니다.
_KAKAO_STAMP = re.compile(r"\[(오전|오후) ?\d{1,2}:\d{2}\]")

# 숫자에 바로 붙은 한글("2시에", "25일", "5678이요")은 단위·조사라 숫자 토큰에 삼킨다.
_TOKEN = re.compile(r"\d[\d-]*[가-힣]*|[가-힣]+")
# 끝에서 조사 하나를 뗀 형도 낱말로 둔다 — "콩이랑"은 콩이+랑(콩이)일 수도 콩+이랑(콩)일 수도 있어 맞는 조사를 모두 떼어 본다.
_PARTICLES = ("이랑", "하고", "한테", "에게", "까지", "부터", "이는", "이가", "이도", "이를",
              "에서", "으로", "은", "는", "이", "가", "을", "를", "도", "랑", "와", "과", "의", "야", "요", "님",
              "에", "로", "께")
# 날짜·시간·인사·예약 낱말은 "누구"가 아니다.
STOP_WORDS = frozenset({
    "안녕하세요", "안녕", "예약", "미용", "가능", "오늘", "내일", "모레", "글피", "이번", "다음", "주",
    "오전", "오후", "저녁", "밤", "낮", "아침", "시", "분", "반", "요일", "이요",
    *(f"{d}요일" for d in _WEEKDAYS),
    # 한 글자 낱말은 이름일 수 있어("봄"·"달") 버리지 않는다 — 흔한 한 글자 말만 뺀다.
    "저", "그", "이", "네", "좀", "꼭", "잘", "더", "또", "안", "못", "뭐", "왜", "나", "너", "애", "것", "게",
    "요", "은", "는", "을", "를", "가", "도", "와", "과", "의", "에", "로",
})
_PHONE_LENGTHS = (4,)   # 뒷자리
_PHONE_MIN = 8          # 전체 번호
MAX_WORDS = 20


@dataclass(frozen=True)
class DraftParse:
    date: date | None
    time: time | None
    guessed_date: bool
    guessed_time: bool
    menu_names: tuple[str, ...]
    guessed_menu: bool
    words: tuple[str, ...]


def parse_draft(text: str, today: date, opens_at: time, closes_at: time, menu_names: Sequence[str]) -> DraftParse:
    text = _KAKAO_STAMP.sub(" ", text)
    day, guessed_day = _parse_date(text, today)
    clock, guessed_clock = _parse_time(text, opens_at, closes_at)
    menus, guessed_menu = _parse_menus(text, menu_names)
    return DraftParse(
        date=day, time=clock, guessed_date=guessed_day, guessed_time=guessed_clock,
        menu_names=menus, guessed_menu=guessed_menu, words=_words(text, menu_names),
    )


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_date(text: str, today: date) -> tuple[date | None, bool]:
    for word, offset in _RELATIVE:
        if word in text:
            return today + timedelta(days=offset), False
    monday = today - timedelta(days=today.weekday())
    if m := _WEEK_DAY.search(text):
        weekday = _WEEKDAYS.index(m.group(2))
        if m.group(1) == "다음":
            return monday + timedelta(days=7 + weekday), True
        day = monday + timedelta(days=weekday)
        return day, day < today   # 이번 주의 지난 요일은 짐작함
    if m := _PLAIN_DAY.search(text):
        ahead = (_WEEKDAYS.index(m.group(1)) - today.weekday()) % 7 or 7   # 오늘은 빼고 가장 가까운 앞날
        return today + timedelta(days=ahead), False
    if m := _MONTH_DAY.search(text) or _SLASH_DAY.search(text):
        day = _safe_date(today.year, int(m.group(1)), int(m.group(2)))
        if day is None:
            return None, False
        if day < today:
            return _safe_date(today.year + 1, day.month, day.day), True   # 지난 날짜면 내년으로 짐작
        return day, False
    if m := _DAY_ONLY.search(text):
        number = int(m.group(1))
        day = _safe_date(today.year, today.month, number)
        if day is None or day < today:
            next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
            day = _safe_date(next_month.year, next_month.month, number)
        return day, day is not None   # 달이 없으니 늘 짐작함
    return None, False


def _clock(hour: int, minute: int) -> time | None:
    return time(hour, minute) if hour < 24 and minute < 60 else None


def _minutes(half: str | None, minute: str | None) -> int:
    return 30 if half else int(minute or 0)


def _parse_time(text: str, opens_at: time, closes_at: time) -> tuple[time | None, bool]:
    if m := _MARKED_TIME.search(text):
        marker, hour, minute = m.group(1), int(m.group(2)), _minutes(m.group(3), m.group(4))
        if marker in _AFTERNOON and hour < 12:
            hour += 12
        elif marker == "낮" and hour < 6:
            hour += 12
        return _clock(hour, minute), False
    if m := _CLOCK_TIME.search(text):
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour >= 12:
            return _clock(hour, minute), False   # 24시 표기는 그대로
    elif m := _HOUR_TIME.search(text):
        hour, minute = int(m.group(1)), _minutes(m.group(2), m.group(3))
    else:
        return None, False
    # 오전·오후 표지가 없다 — 짐작함. 12시 전이면 영업시간 안쪽으로 읽히는 쪽을 고른다.
    clock = _clock(hour, minute)
    if clock is None or hour >= 12:
        return clock, clock is not None
    later = time(hour + 12, minute)
    within = lambda t: opens_at <= t < closes_at   # noqa: E731
    return (later if within(later) and not within(clock) else clock), True


def _parse_menus(text: str, menu_names: Sequence[str]) -> tuple[tuple[str, ...], bool]:
    squeezed = text.replace(" ", "")
    found, guessed = [], False
    for name in menu_names:
        if name in text:
            found.append(name)
        elif name.replace(" ", "") in squeezed:
            found.append(name)
            guessed = True
    return tuple(found), guessed


def _words(text: str, menu_names: Sequence[str]) -> tuple[str, ...]:
    stop = STOP_WORDS | {n for name in menu_names for n in (name, name.replace(" ", ""), *name.split())}
    words: list[str] = []
    for token in _TOKEN.findall(text):
        if token[0].isdigit():
            digits = re.sub(r"\D", "", token)
            if len(digits) in _PHONE_LENGTHS or len(digits) >= _PHONE_MIN:
                words.append(digits)
            continue
        if token in stop:
            continue
        forms = [token] + [token[: -len(p)] for p in _PARTICLES if token.endswith(p) and len(token) > len(p)]
        words += [f for f in forms if f not in stop]
    return tuple(dict.fromkeys(words))[:MAX_WORDS]
