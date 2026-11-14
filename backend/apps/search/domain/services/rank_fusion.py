"""글자 후보와 뜻 후보를 하나의 순위로 — 순위 합치기(RRF)와 같은 방문 접기(⑨ 설계 3.7)."""
from __future__ import annotations

from search.domain.entities.search_document import VISIT_KINDS, Candidate

RRF_K = 60
RESULT_LIMIT = 30
CANDIDATE_LIMIT = 50          # 글자·뜻 후보를 각각 이만큼
LEXICAL_MIN_SIMILARITY = 0.3  # trigram word_similarity — 이보다 낮으면 글자 후보가 아니다(ILIKE 로 든 것은 늘 후보)
SEMANTIC_MIN_SIMILARITY = 0.80  # cosine 유사도 — e5 는 점수가 높게 몰린다. 품질 확인(check_search_quality)으로 맞춘 값


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
