"""받은 문진표를 등록 화면에 옮길 때의 계산(⑪ 설계 3.4). 순수 함수."""
from __future__ import annotations

from customer.domain.entities.intake import UPDATE, IntakeAnswer

MEMO_MAX = 500
# 등록에 꼭 있어야 하는 칸(pets 의 NOT NULL) — 비어 있으면 등록할 때 사장에게 묻는다. 지어내지 않는다.
_REQUIRED = (("species", "species"), ("breed", "breed"), ("sex", "sex"), ("neutered", "neutered"),
             ("weight", "weight_kg"))


def missing_fields(answer: IntakeAnswer) -> tuple[str, ...]:
    """새로 등록할 때 비어 있는 필수 칸의 코드. 다시 받기는 바뀐 것만 적으므로 비어 있다."""
    if answer.mode == UPDATE:
        return ()
    return tuple(code for code, name in _REQUIRED if getattr(answer, name) is None)


def memo_draft(answer: IntakeAnswer) -> str:
    """반려동물 메모의 초안 — 싫어하는 것·원하는 스타일·매장이 더한 질문의 답. 사장이 고친다."""
    lines = []
    if answer.dislikes:
        lines.append(f"조심할 것: {answer.dislikes}")
    if answer.style:
        lines.append(f"원하는 스타일: {answer.style}")
    lines += [f"{label}: {body}" for label, body in answer.extras]
    return "\n".join(lines)


def memo_over(draft: str) -> int:
    """메모 칸(500자)을 넘친 글자 수. 자르지 않는다 — 사장이 줄여야 저장된다."""
    return max(0, len(draft) - MEMO_MAX)
