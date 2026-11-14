import pytest

from search.domain.errors import SearchQueryError
from search.domain.services.search_query import Q_MAX, Q_MIN, clean_query, like_pattern

SECRET = "귀를 만지면 무는 아이"


def test_앞뒤_공백을_떼고_공백류를_빈칸_하나로_줄인다():
    assert clean_query("  귀를\n\n만지면 \t 싫어해요  ") == "귀를 만지면 싫어해요"


@pytest.mark.parametrize("raw", ["발톱", "가" * 100, "  발톱  ", "ab"])
def test_두_자에서_백_자까지는_된다(raw):
    assert Q_MIN <= len(clean_query(raw)) <= Q_MAX


@pytest.mark.parametrize("raw", ["", " ", "가", " 가 ", "\n\t", "가" * 101, "가 " * 51 + "나"])
def test_다듬은_뒤_두_자_미만이거나_백_자를_넘으면_거절한다(raw):
    with pytest.raises(SearchQueryError):
        clean_query(raw)


def test_거절하는_말에_검색어가_들어_있지_않다():
    with pytest.raises(SearchQueryError) as caught:
        clean_query(SECRET * 20)
    assert "귀를" not in str(caught.value) and caught.value.code == "VALIDATION_ERROR"


def test_LIKE_의_특수_글자는_글자_그대로_찾는다():
    assert like_pattern("발톱") == "%발톱%"
    assert like_pattern("100%") == "%100\\%%"
    assert like_pattern("a_b") == "%a\\_b%"
    assert like_pattern("c:\\d") == "%c:\\\\d%"
