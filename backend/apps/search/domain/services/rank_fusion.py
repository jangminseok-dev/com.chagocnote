"""글자 후보와 뜻 후보를 하나의 순위로 — 순위 합치기(RRF)와 같은 방문 접기(⑨ 설계 3.7)."""
from __future__ import annotations

from search.domain.entities.search_document import VISIT_KINDS, Candidate

RRF_K = 60
RESULT_LIMIT = 30
CANDIDATE_LIMIT = 50          # 글자 후보의 수
LEXICAL_MIN_SIMILARITY = 0.3  # trigram word_similarity — 이보다 낮으면 글자 후보가 아니다(ILIKE 로 든 것은 늘 후보)
# 뜻 후보 — 이 모델(e5-small)은 cosine 유사도가 높게 몰린다: 관계없는 글도 0.79~0.82, 맞는 글은 0.83~0.89 다
# (scripts/check_search_quality.py 로 잰 값, 결정 기록 013). 바닥만으로는 관계없는 글을 못 거르므로, 가장 가까운
# 글에서 여유 안쪽인 것만 몇 개 남긴다. 글자가 그대로 든 글은 글자 후보가 따로 넉넉히 받는다.
SEMANTIC_MIN_SIMILARITY = 0.80   # 바닥 — 이보다 낮으면 가장 가까워도 후보가 아니다
SEMANTIC_MARGIN = 0.02           # 가장 가까운 글의 유사도에서 이만큼 안쪽까지
SEMANTIC_LIMIT = 5               # 뜻 후보의 수 — 맞는 글이 없을 때 딸려 나오는 "그나마 가까운 글"도 이 수를 넘지 않는다


def fuse(lexical: list[int], semantic: list[int]) -> list[int]:
    """문서 ID 의 순위 목록 둘 → 점수 Σ 1/(k + 순위)(순위는 1부터) 내림차순. 점수가 같으면 글자 쪽이,
    그 안에서는 먼저 나온 것이 앞이다."""
    score: dict[int, float] = {}
    order: dict[int, int] = {}
    for ranked in (lexical, semantic):
        for rank, doc_id in enumerate(ranked, start=1):
            score[doc_id] = score.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
            order.setdefault(doc_id, len(order))
    return sorted(score, key=lambda doc_id: (-score[doc_id], order[doc_id]))


def collapse_visits(ranked: list[Candidate]) -> list[Candidate]:
    """같은 방문의 케어 노트·내부 메모·예약 메모가 함께 걸리면 가장 앞의 하나만 남긴다 — 한 방문이 결과를 채우지 않게."""
    seen: set[int] = set()
    kept = []
    for c in ranked:
        if c.kind in VISIT_KINDS and c.visit_id is not None:
            if c.visit_id in seen:
                continue
            seen.add(c.visit_id)
        kept.append(c)
    return kept
