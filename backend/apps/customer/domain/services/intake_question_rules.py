"""매장이 더하는 질문의 규칙(⑪ 설계 3.4). 순수 함수 — 오류 글에 매장이 적은 글을 싣지 않는다."""
from __future__ import annotations

from customer.domain.entities.intake import QUESTION_LABEL_MAX, QUESTION_MAX, QuestionDraft
from customer.domain.errors import CustomerInputError


def check_questions(drafts: tuple[QuestionDraft, ...], known_ids: frozenset[int]) -> None:
    """known_ids 는 이 매장의 살아 있는 질문이다 — 그 밖의 번호(남의 매장·지운 질문)는 받지 않는다."""
    if len(drafts) > QUESTION_MAX:
        raise CustomerInputError(f"질문은 {QUESTION_MAX}개까지 더할 수 있습니다.")
    given = [draft.id for draft in drafts if draft.id is not None]
    if len(set(given)) != len(given) or any(question_id not in known_ids for question_id in given):
        raise CustomerInputError("없는 질문입니다. 다시 불러와 주세요.")
    for draft in drafts:
        if not draft.label.strip():
            raise CustomerInputError("질문을 비워 둘 수 없습니다.")
        if len(draft.label) > QUESTION_LABEL_MAX:
            raise CustomerInputError(f"질문은 {QUESTION_LABEL_MAX}자까지 적을 수 있습니다.")
