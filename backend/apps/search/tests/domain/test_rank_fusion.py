from search.domain.services.rank_fusion import RESULT_LIMIT, RRF_K, collapse_visits, fuse
from search.tests.helpers.builders import candidate


def test_두_쪽에_다_있는_문서가_앞에_온다():
    assert fuse([1, 2, 3], [3, 4]) == [3, 1, 2, 4]     # 2 와 4 는 점수가 같다 — 글자 쪽이 앞


def test_한쪽에만_있어도_든다():
    assert fuse([1, 2], []) == [1, 2]
    assert fuse([], [5, 6]) == [5, 6]
    assert fuse([], []) == []


def test_점수가_같으면_글자로_걸린_쪽이_앞이다():
    assert fuse([1], [2]) == [1, 2]
    assert fuse([1, 2], [3, 4]) == [1, 3, 2, 4]


def test_상수는_설계의_값이다():
    assert (RRF_K, RESULT_LIMIT) == (60, 30)


def test_같은_방문의_글이_함께_걸리면_가장_앞의_하나만_남는다():
    ranked = [
        candidate(1, "internal_note", visit_id=7), candidate(2, "pet_memo", source_id=101),
        candidate(3, "care_note", visit_id=7), candidate(4, "visit_memo", visit_id=8),
        candidate(5, "visit_memo", visit_id=7), candidate(6, "pet_memo", source_id=102),
    ]
    assert [c.id for c in collapse_visits(ranked)] == [1, 2, 4, 6]


def test_방문이_아닌_글은_접지_않는다():
    ranked = [candidate(1, "condition_note", source_id=41, pet_id=101),
              candidate(2, "condition_note", source_id=42, pet_id=101), candidate(3, "pet_memo", source_id=101)]
    assert [c.id for c in collapse_visits(ranked)] == [1, 2, 3]
