import pytest

from notification.domain.services.templates import (
    TEMPLATES,
    TEXT_VERSION,
    euc_kr_bytes,
    expiry_label,
    format_date,
    format_time,
    format_when,
    render,
    sms_channel,
    target_label,
    variables_for,
)
from notification.domain.value_objects.message_kind import (
    CANCEL,
    CHANGE,
    CONFIRM,
    KINDS,
    NEXT_VISIT,
    REMINDER,
    REPORT,
)
from notification.tests.helpers.builders import TZ, kst

STARTS = kst(10, 15, 14)          # 10월 15일(목) 14:00
PREVIOUS = kst(10, 14, 11)        # 10월 14일(수) 11:00
URL = "https://chagocnote.com/r/" + "a" * 43     # 알림장 토큰은 32바이트 base64 — 43자

# 설계 6.3 표 그대로 — 알림톡 문안은 줄 단위, 문자용은 한 줄
DESIGN = {
    CONFIRM: (
        ["[#{매장명}] 예약 접수 안내", "#{대상}의 예약이 접수되었어요.", "일시: #{일시}", "변경·취소는 매장으로 연락해 주세요."],
        "[#{매장명}] #{일시} 예약이 접수되었어요.", None,
    ),
    REMINDER: (
        ["[#{매장명}] 내일 예약 안내", "#{대상}의 예약이 내일이에요.", "일시: #{일시}", "늦거나 못 오시면 미리 연락해 주세요."],
        "[#{매장명}] 내일 #{시각} 예약을 잊지 마세요.", None,
    ),
    CHANGE: (
        ["[#{매장명}] 예약 변경 안내", "#{대상}의 예약 일시가 바뀌었어요.", "변경 전: #{이전일시}", "변경 후: #{일시}"],
        "[#{매장명}] 예약이 #{일시}로 바뀌었어요.", None,
    ),
    CANCEL: (
        ["[#{매장명}] 예약 취소 안내", "매장 사정으로 #{대상}의 #{일시} 예약이 취소되었어요. 죄송합니다.",
         "다시 예약하시려면 매장으로 연락해 주세요."],
        "[#{매장명}] #{일시} 예약이 매장 사정으로 취소되었어요.", None,
    ),
    REPORT: (
        ["[#{매장명}] 미용 알림장", "#{대상}의 오늘 미용 알림장이 도착했어요.", "#{기간안내}"],
        "[#{매장명}] 알림장 #{링크}", "알림장 보기",
    ),
    NEXT_VISIT: (
        ["[#{매장명}] 미용 주기 안내", "#{대상}의 지난 미용이 #{지난일}이었어요.", "#{간격}주 정도마다 미용하면 좋아요.",
         "예약은 매장으로 연락해 주세요."],
        "[#{매장명}] #{대상} 미용한 지 #{간격}주가 지났어요.", None,
    ),
}


def _all_variables(kind: str) -> dict[str, str]:
    return variables_for(kind, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ,
                         previous_starts_at=PREVIOUS, url=URL, expires_at=kst(11, 2, 14),
                         last_visit_at=STARTS, interval_weeks=4)


def test_문안은_여섯_종류이고_판은_1이다():
    assert TEXT_VERSION == 1
    assert tuple(TEMPLATES) == KINDS


@pytest.mark.parametrize("kind", KINDS)
def test_문안은_설계_6_3_과_글자까지_같다(kind):
    lines, sms_body, button = DESIGN[kind]
    text = TEMPLATES[kind]
    assert text.kind == kind
    assert text.body == "\n".join(lines)
    assert text.sms_body == sms_body
    assert text.button_label == button


def test_알림톡_본문에는_링크_변수가_없고_문자용에만_있다():
    assert "#{링크}" not in TEMPLATES[REPORT].body
    assert "#{링크}" in TEMPLATES[REPORT].sms_body


# 변수


def test_변수는_종류마다_필요한_것만_준다():
    assert variables_for(CONFIRM, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ) == {
        "매장명": "두부네 미용실", "대상": "두부", "일시": "10월 15일(목) 14:00",
    }
    assert variables_for(REMINDER, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ) == {
        "매장명": "두부네 미용실", "대상": "두부", "일시": "10월 15일(목) 14:00", "시각": "14:00",
    }
    assert variables_for(CHANGE, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ,
                         previous_starts_at=PREVIOUS) == {
        "매장명": "두부네 미용실", "대상": "두부", "일시": "10월 15일(목) 14:00", "이전일시": "10월 14일(수) 11:00",
    }
    assert variables_for(CANCEL, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ) == {
        "매장명": "두부네 미용실", "대상": "두부", "일시": "10월 15일(목) 14:00",
    }
    assert variables_for(REPORT, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ,
                         url=URL, expires_at=kst(11, 2, 14)) == {
        "매장명": "두부네 미용실", "대상": "두부", "기간안내": "11월 2일까지 열려요.", "링크": URL,
    }
    assert variables_for(NEXT_VISIT, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ,
                         last_visit_at=STARTS, interval_weeks=4) == {
        "매장명": "두부네 미용실", "대상": "두부", "지난일": "10월 15일(목)", "간격": "4",
    }


@pytest.mark.parametrize(("kind", "missing"), [
    (CHANGE, "previous_starts_at"), (REPORT, "url"), (NEXT_VISIT, "last_visit_at"), (NEXT_VISIT, "interval_weeks"),
])
def test_필요한_값이_빠지면_프로그래밍_오류다(kind, missing):
    kwargs = dict(previous_starts_at=PREVIOUS, url=URL, last_visit_at=STARTS, interval_weeks=4)
    kwargs.pop(missing)
    with pytest.raises(ValueError):
        variables_for(kind, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ, **kwargs)


def test_알림장의_기간이_없으면_언제든_열_수_있다고_한다():
    variables = variables_for(REPORT, shop_name="두부네 미용실", target="두부", starts_at=STARTS, tz=TZ, url=URL)
    assert variables["기간안내"] == "언제든 열 수 있어요."


# 치환


@pytest.mark.parametrize("kind", KINDS)
def test_치환하면_남는_변수_자리가_없다(kind):
    rendered = render(kind, _all_variables(kind))
    assert "#{" not in rendered.text
    assert "#{" not in rendered.sms_text


def test_접수_문안을_채운_모습():
    rendered = render(CONFIRM, _all_variables(CONFIRM))
    assert rendered.text == (
        "[두부네 미용실] 예약 접수 안내\n두부의 예약이 접수되었어요.\n일시: 10월 15일(목) 14:00\n변경·취소는 매장으로 연락해 주세요."
    )
    assert rendered.sms_text == "[두부네 미용실] 10월 15일(목) 14:00 예약이 접수되었어요."
    assert rendered.button_url is None
    assert rendered.variables == {"#{매장명}": "두부네 미용실", "#{대상}": "두부", "#{일시}": "10월 15일(목) 14:00"}


def test_알림장은_버튼_주소가_있고_본문에는_주소가_없다():
    rendered = render(REPORT, _all_variables(REPORT))
    assert rendered.button_url == URL
    assert URL not in rendered.text
    assert rendered.sms_text == f"[두부네 미용실] 알림장 {URL}"


def test_값에_든_변수_모양은_글자로_남는다():
    """이름이 '#{매장명}' 이어도 한 번만 치환한다 — 업체도 값을 글자 그대로 넣는다."""
    variables = variables_for(CONFIRM, shop_name="두부네 미용실", target="#{매장명}", starts_at=STARTS, tz=TZ)
    rendered = render(CONFIRM, variables)
    assert rendered.text.startswith("[두부네 미용실] 예약 접수 안내\n#{매장명}의 예약이 접수되었어요.")
    assert rendered.variables["#{대상}"] == "#{매장명}"


def test_긴_값은_200자에서_자르고_주소는_자르지_않는다():
    long_url = "https://chagocnote.com/r/" + "a" * 300
    variables = variables_for(REPORT, shop_name="가" * 250, target="두부", starts_at=STARTS, tz=TZ, url=long_url)
    rendered = render(REPORT, variables)
    assert rendered.variables["#{매장명}"] == "가" * 200
    assert rendered.text.startswith("[" + "가" * 200 + "] 미용 알림장")
    assert rendered.button_url == long_url
    assert rendered.sms_text.endswith(long_url)


# 문자 길이 — EUC-KR 90바이트


def test_한글_45자는_sms_46자는_lms():
    assert euc_kr_bytes("가" * 45) == 90
    assert sms_channel("가" * 45) == "sms"
    assert sms_channel("가" * 46) == "lms"


def test_알림장_문자는_실제_길이의_주소를_넣으면_lms_다():
    rendered = render(REPORT, _all_variables(REPORT))
    assert sms_channel(rendered.sms_text) == "lms"
    rendered = render(CONFIRM, _all_variables(CONFIRM))
    assert sms_channel(rendered.sms_text) == "sms"


# 표기


def test_대상은_반려동물_이름_없으면_보호자_이름에_님():
    assert target_label("두부", "김차곡") == "두부"
    assert target_label(None, "김차곡") == "김차곡님"


def test_일시_표기는_월_일_한글_요일_시각():
    assert format_when(kst(10, 15, 14), TZ) == "10월 15일(목) 14:00"
    assert format_when(kst(10, 18, 9, 5), TZ) == "10월 18일(일) 09:05"
    assert format_when(kst(11, 2, 0, 30), TZ) == "11월 2일(월) 00:30"     # UTC 로는 전날 — 매장 시간대로
    assert format_time(kst(10, 15, 14), TZ) == "14:00"
    assert format_date(kst(10, 15, 14), TZ) == "10월 15일(목)"


def test_기간_안내_둘():
    assert expiry_label(kst(11, 2, 14), TZ) == "11월 2일까지 열려요."
    assert expiry_label(None, TZ) == "언제든 열 수 있어요."
