import pytest

from visit.domain.errors import VisitInputError
from visit.domain.services.revisit_rules import DEFAULT_REVISIT_MESSAGE, check_revisit_settings, fill_message
from visit.domain.value_objects.revisit_settings import DEFAULT_REVISIT_SETTINGS, RevisitSettings


def test_처음_값은_4주_7일_처음_글_세기_6번_7일이다():
    s = DEFAULT_REVISIT_SETTINGS
    assert (s.default_cycle_weeks, s.revisit_soon_days, s.revisit_message, s.count_unsent_reports) == (4, 7, None, True)
    assert (s.cycle_sample_visits, s.cycle_min_gap_days) == (6, 7)
    rules = s.rules()
    assert (rules.default_weeks, rules.soon_days, rules.sample_visits, rules.min_gap_days) == (4, 7, 6, 7)


@pytest.mark.parametrize("changes", [
    {"default_cycle_weeks": 0}, {"default_cycle_weeks": 53},
    {"revisit_soon_days": 0}, {"revisit_soon_days": 31},
    {"cycle_sample_visits": 2}, {"cycle_sample_visits": 13},
    {"cycle_min_gap_days": -1}, {"cycle_min_gap_days": 29},
    {"revisit_message": ""}, {"revisit_message": "   \n "}, {"revisit_message": "가" * 301},
    {"revisit_message": "안녕‮하세요"},
])
def test_범위_밖이나_빈_글은_거절한다(changes):
    with pytest.raises(VisitInputError):
        check_revisit_settings(RevisitSettings(**{**DEFAULT_REVISIT_SETTINGS.__dict__, **changes}))


@pytest.mark.parametrize("changes", [
    {"default_cycle_weeks": 1}, {"default_cycle_weeks": 52}, {"revisit_soon_days": 30},
    {"cycle_sample_visits": 3}, {"cycle_sample_visits": 12}, {"cycle_min_gap_days": 0}, {"cycle_min_gap_days": 28},
    {"revisit_message": "가" * 300}, {"revisit_message": "첫 줄\n둘째 줄"}, {"revisit_message": "칩이 없는 글"},
])
def test_경계_안은_받는다(changes):
    check_revisit_settings(RevisitSettings(**{**DEFAULT_REVISIT_SETTINGS.__dict__, **changes}))


def test_안내_글은_매장_아이_주를_채운다():
    assert DEFAULT_REVISIT_MESSAGE == (
        "안녕하세요, {매장}예요.\n{아이}가 미용한 지 {주}주가 됐어요.\n편하신 날 알려 주시면 예약 잡아 드릴게요."
    )
    assert fill_message(None, shop="Hiss Haus", pet="콩이", weeks=6) == (
        "안녕하세요, Hiss Haus예요.\n콩이가 미용한 지 6주가 됐어요.\n편하신 날 알려 주시면 예약 잡아 드릴게요."
    )
    assert fill_message("{아이} {아이} {주}주 · {모르는칸}", shop="", pet="두부", weeks=3) == "두부 두부 3주 · {모르는칸}"
