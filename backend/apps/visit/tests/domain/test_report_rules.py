from datetime import timedelta

import pytest

from visit.domain.entities.visit_record import RecordMedia
from visit.domain.errors import ReportEmptyError, VisitInputError, VisitNoRecordYetError, VisitNotCompletedError
from visit.domain.services.report_rules import (
    MAX_HIDDEN,
    carry_hidden,
    check_hidden_ids,
    check_not_empty,
    check_sendable,
    check_settings,
    expires_at_for,
    hide,
    report_cover_media_id,
    visible_media,
)
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, LINK_DAYS, ReportSettings
from visit.tests.helpers.builders import but, kst, record, visit

NOW = kst(9, 28, 15)


def _m(media_id, kind="photo", phase="after", order=0, hidden=False):
    return RecordMedia(media_id=media_id, kind=kind, phase=phase, sort_order=order, hidden=hidden)


def _record(*media, care_note=None):
    return but(record(1, care_note=care_note), media=tuple(media))


# 저장소가 주는 순서(전 → 후, 그 안에서 sort_order)대로 둔다.
MIXED = (_m(1, phase="before", order=0), _m(2, "video", "before", 1), _m(3, order=0), _m(4, order=1))


def test_처음_설정은_30일이고_메뉴와_매장_정보만_보인다():
    assert DEFAULT_REPORT_SETTINGS == ReportSettings(
        link_days=30, show_menus=True, show_shop_info=True, show_weight=False, show_amount=False)
    assert LINK_DAYS == (7, 30)


@pytest.mark.parametrize("days", [7, 30])
def test_링크는_보낸_때부터_설정한_날수만큼_열린다(days):
    assert expires_at_for(NOW, days) == NOW + timedelta(days=days)


def test_기간이_없으면_무기한이다():
    assert expires_at_for(NOW, None) is None


@pytest.mark.parametrize("days", [7, 30, None])
def test_기간은_7일_30일_무기한_가운데_하나다(days):
    check_settings(but(DEFAULT_REPORT_SETTINGS, link_days=days))


@pytest.mark.parametrize("days", [0, 1, 8, 31, -7, 365])
def test_그_밖의_기간은_VALIDATION_ERROR_다(days):
    with pytest.raises(VisitInputError):
        check_settings(but(DEFAULT_REPORT_SETTINGS, link_days=days))


@pytest.mark.parametrize("hidden_ids", [(), (3,), (1, 2, 3, 4)])
def test_이_기록의_미디어는_뺄_수_있다(hidden_ids):
    check_hidden_ids(_record(*MIXED), hidden_ids)


def test_같은_미디어를_두_번_빼면_VALIDATION_ERROR_다():
    with pytest.raises(VisitInputError):
        check_hidden_ids(_record(*MIXED), (3, 3))


def test_이_기록의_것이_아닌_미디어를_빼면_VALIDATION_ERROR_다():
    with pytest.raises(VisitInputError):
        check_hidden_ids(_record(*MIXED), (3, 99))
    with pytest.raises(VisitInputError):
        check_hidden_ids(_record(), (3,))


def test_뺄_수_있는_미디어는_33개까지다():
    many = _record(*(_m(i, order=i) for i in range(1, MAX_HIDDEN + 2)))   # 미디어 34개
    assert MAX_HIDDEN == 33
    check_hidden_ids(many, tuple(range(1, MAX_HIDDEN + 1)))
    with pytest.raises(VisitInputError):
        check_hidden_ids(many, tuple(range(1, MAX_HIDDEN + 2)))


def test_빼면_고른_것만_hidden_이고_순서와_다른_값은_그대로다():
    assert hide(_record(*MIXED), (2, 3)) == (
        _m(1, phase="before", order=0), _m(2, "video", "before", 1, hidden=True), _m(3, order=0, hidden=True),
        _m(4, order=1))


def test_다시_빼면_앞서_뺀_것은_되살아난다():
    before = _record(_m(1, hidden=True), _m(2, order=1))
    assert hide(before, (2,)) == (_m(1), _m(2, order=1, hidden=True))
    assert hide(before, ()) == (_m(1), _m(2, order=1))


def test_기록을_다시_저장하면_뺀_표시를_미디어_ID_로_옮긴다():
    previous = (_m(1, hidden=True), _m(2, order=1), _m(3, order=2, hidden=True))
    # 3은 사라졌고, 1은 전 사진 칸으로 옮겼고, 9는 새로 붙었다.
    media = (_m(9, "video", "after", 0), _m(2, order=1), _m(1, phase="before", order=0))

    assert carry_hidden(previous, media) == (
        _m(9, "video", "after", 0), _m(2, order=1), _m(1, phase="before", order=0, hidden=True))


def test_앞선_기록이_없으면_모두_보인다():
    assert carry_hidden((), (_m(1), _m(2, order=1))) == (_m(1), _m(2, order=1))


def test_보이는_미디어는_후_먼저_전_나중이고_그_안에서_순서대로다():
    shuffled = _record(_m(2, "video", "before", 1), _m(4, order=1), _m(1, phase="before", order=0), _m(3, order=0))
    assert [m.media_id for m in visible_media(shuffled)] == [3, 4, 1, 2]


def test_뺀_미디어는_보이지_않는다():
    hidden = _record(*hide(_record(*MIXED), (3, 1)))
    assert visible_media(hidden) == (_m(4, order=1), _m(2, "video", "before", 1))


def test_대표는_빼지_않은_것_가운데_후_사진_전_사진_영상_순이다():
    assert report_cover_media_id(_record(*MIXED)) == 3
    assert report_cover_media_id(_record(*hide(_record(*MIXED), (3,)))) == 4
    assert report_cover_media_id(_record(*hide(_record(*MIXED), (3, 4)))) == 1
    assert report_cover_media_id(_record(*hide(_record(*MIXED), (3, 4, 1)))) == 2


def test_전부_빼면_대표가_없다():
    assert report_cover_media_id(_record(*hide(_record(*MIXED), (1, 2, 3, 4)))) is None
    assert report_cover_media_id(_record()) is None


def test_완료한_방문의_기록은_보낼_수_있다():
    check_sendable(visit(status="completed"), _record(*MIXED), (3,))


@pytest.mark.parametrize("status", ["reserved", "in_progress", "canceled", "no_show"])
def test_완료가_아닌_방문은_VISIT_NOT_COMPLETED(status):
    with pytest.raises(VisitNotCompletedError):
        check_sendable(visit(status=status), _record(*MIXED), ())


def test_완료가_아니면_기록이_없어도_VISIT_NOT_COMPLETED_가_먼저다():
    with pytest.raises(VisitNotCompletedError):
        check_sendable(visit(status="in_progress"), None, ())


def test_기록이_없는_완료_방문은_VISIT_NO_RECORD_YET():
    with pytest.raises(VisitNoRecordYetError):
        check_sendable(visit(status="completed"), None, ())


def test_보낼_때도_뺄_미디어를_검사한다():
    with pytest.raises(VisitInputError):
        check_sendable(visit(status="completed"), _record(*MIXED), (99,))


def test_보내기_검사는_빈_알림장을_보지_않는다():
    """빈 알림장은 링크를 새로 만들 때만 막는다 — 보낸 뒤 사진을 전부 빼는 것은 된다(설계 7.4)."""
    check_sendable(visit(status="completed"), _record(*MIXED), (1, 2, 3, 4))
    check_sendable(visit(status="completed"), _record(), ())


@pytest.mark.parametrize("care_note", [None, "", "   ", "\n\t "])
def test_보이는_미디어도_메모도_없으면_REPORT_EMPTY(care_note):
    with pytest.raises(ReportEmptyError):
        check_not_empty(_record(care_note=care_note), ())
    with pytest.raises(ReportEmptyError):
        check_not_empty(_record(*MIXED, care_note=care_note), (1, 2, 3, 4))


def test_메모만_있어도_보낼_수_있다():
    check_not_empty(_record(care_note="발톱을 짧게 다듬었어요"), ())
    check_not_empty(_record(*MIXED, care_note="발톱을 짧게 다듬었어요"), (1, 2, 3, 4))


@pytest.mark.parametrize("care_note", [None, "", "   "])
def test_미디어가_하나라도_남으면_보낼_수_있다(care_note):
    check_not_empty(_record(*MIXED, care_note=care_note), (1, 2, 3))


def test_빈_알림장은_이번에_보낸_목록으로_판단한다():
    """앞서 뺀 표시(hidden)가 아니라 이번 요청의 hidden_ids 가 기준이다 — 저장하기 전에 검사한다."""
    all_hidden = _record(_m(1, hidden=True))
    check_not_empty(all_hidden, ())
    with pytest.raises(ReportEmptyError):
        check_not_empty(_record(_m(1)), (1,))


# ── 알림장 끝의 리뷰 주소(⑫) ─────────────────────────────────────────────────────────────

from dataclasses import replace  # noqa: E402

from visit.domain.services.report_rules import DEFAULT_REVIEW_TEXT, check_review, review_of  # noqa: E402
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS  # noqa: E402


@pytest.mark.parametrize("url", [
    "http://naver.me/abc", "javascript:alert(1)", "https://user@evil.example/x", "https://naver.me/a b",
    "https://", "https://naver.me/" + "a" * 290, "https://naver.me/\x07", "ftp://naver.me/x",
    # 최종 검토 — 대괄호가 짝이 안 맞는 호스트(urlsplit 이 ValueError), 눈에 안 보이는 문자, 틀린 포트
    "https://naver.me]", "https://[", "https://[abc]/x", "https://a.com/\x9b", "https://a.com/\u200b",
    "https://a.com:abc/x",
])
def test_리뷰_주소는_https_이고_호스트가_있고_계정정보_공백_제어문자가_없고_300자까지다(url):
    with pytest.raises(VisitInputError):
        check_review(url, None)


@pytest.mark.parametrize("text", ["가" * 61, "첫 줄\n둘째 줄", "www.evil.example 로 오세요", "http 주소를 누르세요", "탭\t글",
                                  "후기\u202e요세주", "첫 줄\u2028둘째", "보이지\u200b않는"])
def test_리뷰_문구는_60자이고_줄바꿈_제어문자_주소를_담지_않는다(text):
    with pytest.raises(VisitInputError):
        check_review("https://naver.me/abc", text)


def test_맞는_주소와_문구는_받는다():
    check_review("https://m.place.naver.com/place/123/review", "후기 한 줄 부탁드려요")
    check_review(None, None)


def test_주소가_없거나_그_알림장이_뺐으면_리뷰_줄이_없고_문구가_비면_기본_문구다():
    on = replace(DEFAULT_REPORT_SETTINGS, review_url="https://naver.me/abc", review_text=None)

    assert review_of(DEFAULT_REPORT_SETTINGS, True) == (None, None)
    assert review_of(on, False) == (None, None)
    assert review_of(on, True) == ("https://naver.me/abc", DEFAULT_REVIEW_TEXT)
    assert review_of(replace(on, review_text="후기 부탁드려요"), True) == ("https://naver.me/abc", "후기 부탁드려요")
    assert DEFAULT_REVIEW_TEXT == "미용이 마음에 드셨다면 후기를 남겨 주세요"


def test_대문자_https_는_받되_소문자로_바꿔_둔다():
    from visit.domain.services.report_rules import normalized_review_url

    assert normalized_review_url("HTTPS://Naver.me/Abc") == "https://Naver.me/Abc"
    assert normalized_review_url(None) is None

