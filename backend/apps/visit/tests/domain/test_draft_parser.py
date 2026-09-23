"""카톡 초안 해석기 — 표 기반. 오늘은 2026-09-24(목), 영업시간 10:00~19:00, 기본 메뉴표."""
from datetime import date, time

import pytest

from visit.domain.services.draft_parser import MAX_WORDS, parse_draft

TODAY = date(2026, 9, 24)   # 목요일
OPENS, CLOSES = time(10, 0), time(19, 0)
MENUS = ["목욕", "위생", "부분 미용", "전체 미용", "스포팅"]


def parse(text, today=TODAY, opens=OPENS, closes=CLOSES, menus=MENUS):
    return parse_draft(text, today, opens, closes, menus)


@pytest.mark.parametrize("text, expected, guessed", [
    ("내일 2시", date(2026, 9, 25), False),
    ("모레 갈게요", date(2026, 9, 26), False),
    ("내일모레 괜찮아요?", date(2026, 9, 26), False),          # 긴 표현이 이긴다
    ("글피", date(2026, 9, 27), False),
    ("오늘 저녁", date(2026, 9, 24), False),
    ("이번 주 금요일", date(2026, 9, 25), False),
    ("이번주 월요일", date(2026, 9, 21), True),                # 이번 주의 지난 요일
    ("다음 주 월요일", date(2026, 9, 28), True),               # 다음 주는 늘 짐작함
    ("다음주 수요일", date(2026, 9, 30), True),
    ("금요일 괜찮을까요", date(2026, 9, 25), False),
    ("목요일에요", date(2026, 10, 1), False),                  # 오늘은 빼고 가장 가까운 앞날
    ("수요일", date(2026, 9, 30), False),
    ("10월 2일", date(2026, 10, 2), False),
    ("10월2일", date(2026, 10, 2), False),
    ("10/2", date(2026, 10, 2), False),
    ("9월 3일", date(2027, 9, 3), True),                       # 지난 날짜는 내년으로 짐작
    ("2일", date(2026, 10, 2), True),                          # 달이 없고 지났으면 다음 달
    ("25일", date(2026, 9, 25), True),
    ("24일", date(2026, 9, 24), True),                         # 오늘은 지난 게 아니다
    ("11일", date(2026, 10, 11), True),                        # 1일로 읽지 않는다
    ("123일", None, False),                                    # 세 자리 숫자의 뒤 두 자리를 날짜로 읽지 않는다
    ("1월 1일", date(2027, 1, 1), True),
    ("2/30", None, False),                                     # 없는 날짜
    ("10분 뒤", None, False),
    ("31일", date(2026, 10, 31), True),                        # 이번 달에 없으면 다음 달
    ("안녕하세요", None, False),
])
def test_날짜_표현(text, expected, guessed):
    result = parse(text)
    assert (result.date, result.guessed_date) == (expected, guessed)


def test_달_없는_날짜는_이번_달_아니면_다음_달까지만_본다():
    assert parse("30일", today=date(2026, 2, 10)).date == date(2026, 3, 30)   # 2월엔 없다
    assert parse("30일", today=date(2026, 3, 31)).date == date(2026, 4, 30)   # 3/30 은 지났다
    assert parse("31일", today=date(2026, 4, 1)).date == date(2026, 5, 31)    # 4/31 은 없다
    assert parse("32일", today=date(2026, 4, 1)).date is None


@pytest.mark.parametrize("text, expected, guessed", [
    ("오후 2시", time(14, 0), False),
    ("오후2시반", time(14, 30), False),
    ("2시", time(14, 0), True),                                # 10~19시 안쪽으로
    ("11시", time(11, 0), True),
    ("6시", time(18, 0), True),
    ("10시", time(10, 0), True),                               # 10시는 안, 22시는 밖
    ("12시", time(12, 0), True),                               # 표지가 없으면 늘 짐작함
    ("2시간 걸려요", None, False),                              # "시간"의 "시"는 시각이 아니다
    ("[김민지] [오후 2:31] 내일 3시 콩이 목욕", time(15, 0), True),   # 카톡 머리말의 2:31 은 보낸 시각이다
    ("오후 2시간쯤 뒤 4시", time(16, 0), True),                 # 표지는 "2시간"에 붙어 4시는 표지 없음
    ("15시", time(15, 0), True),
    ("저녁 7시 반", time(19, 30), False),
    ("14:00", time(14, 0), False),
    ("2:30", time(14, 30), True),
    ("오전 10시 30분", time(10, 30), False),
    ("아침 9시", time(9, 0), False),
    ("낮 12시", time(12, 0), False),
    ("낮 2시", time(14, 0), False),
    ("밤 9시", time(21, 0), False),
    ("오전 13시", time(13, 0), False),
    ("3시반", time(15, 30), True),
    ("2시 30분", time(14, 30), True),
    ("25시", None, False),
    ("오후 2시 70분", None, False),
    ("두 시", None, False),
])
def test_시각_표현(text, expected, guessed):
    result = parse(text)
    assert (result.time, result.guessed_time) == (expected, guessed)


def test_표지_없는_시각은_영업시간에_따라_다르게_읽는다():
    assert parse("6시", opens=time(6, 0), closes=time(15, 0)).time == time(6, 0)
    assert parse("8시", opens=time(20, 0), closes=time(23, 0)).time == time(20, 0)
    assert parse("3시", opens=time(10, 0), closes=time(12, 0)).time == time(3, 0)   # 둘 다 밖이면 그대로


@pytest.mark.parametrize("text, expected, guessed", [
    ("전체 미용 부탁드려요", ("전체 미용",), False),
    ("전체미용이요", ("전체 미용",), True),                    # 공백을 빼야 맞으면 짐작함
    ("위생이랑 목욕", ("목욕", "위생"), False),                # 메뉴표 순서
    ("미용 예약", (), False),
    ("스포팅", (), False),
])
def test_메뉴(text, expected, guessed):
    result = parse(text, menus=["목욕", "위생", "부분 미용", "전체 미용"])
    assert (result.menu_names, result.guessed_menu) == (expected, guessed)


@pytest.mark.parametrize("text, expected", [
    ("콩이랑 두부 내일 오후 2시 목욕 부탁드려요", ("콩이랑", "콩", "콩이", "두부", "부탁드려요", "부탁드려")),
    ("콩이가 요즘", ("콩이가", "콩", "콩이", "요즘")),
    ("010-1234-5678 김민지입니다", ("01012345678", "김민지입니다")),
    ("5678이요", ("5678",)),                                   # 숫자에 붙은 한글은 단위·조사다
    ("5678 이요", ("5678",)),
    ("콩이 2시에 목욕탕에서", ("콩이", "콩", "목욕탕에서", "목욕탕")),
    ("123 456", ()),                                           # 뒷자리 4자리도 전체 8자리도 아니다
    ("콩이 콩이 콩이", ("콩이", "콩")),
    ("안녕하세요 월요일 오전 예약 가능할까요", ("가능할까요", "가능할까")),
    ("저 내일 갈게요", ("갈게요", "갈게")),                     # 흔한 한 글자 말은 낱말이 아니다
    ("봄 내일 갈게요", ("봄", "갈게요", "갈게")),                # 한 글자 이름은 낱말이다(customer 가 통단어로 찾는다)
    ("[김민지] [오후 2:31] 콩이 내일요", ("김민지", "콩이", "콩", "내일요")),   # 카톡 머리말의 시각은 지우고 보낸 사람은 남긴다
    ("부분 미용 부분미용", ()),                                 # 메뉴 이름과 그 조각은 낱말이 아니다
])
def test_누구_낱말(text, expected):
    assert parse(text).words == expected


def test_낱말은_스무_개까지다():
    names = " ".join(f"이름{chr(0xAC00 + i)}" for i in range(25))
    assert len(parse(names).words) == MAX_WORDS


def test_한_문장에서_날짜_시각_메뉴_낱말을_함께_뽑는다():
    result = parse("안녕하세요 콩이 내일 오후 2시에 목욕 가능할까요?")
    assert (result.date, result.time, result.menu_names) == (date(2026, 9, 25), time(14, 0), ("목욕",))
    assert result.words == ("콩이", "콩", "가능할까요", "가능할까")
    assert (result.guessed_date, result.guessed_time, result.guessed_menu) == (False, False, False)
