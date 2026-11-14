from __future__ import annotations

from search.domain.errors import SearchQueryError

Q_MIN = 2
Q_MAX = 100


def clean_query(raw: str) -> str:
    """공백류(줄바꿈·탭)를 빈칸 하나로 줄이고 앞뒤를 뗀다. 2~100자가 아니면 SearchQueryError.
    오류 메시지에 검색어를 넣지 않는다."""
    q = " ".join(raw.split())
    if not Q_MIN <= len(q) <= Q_MAX:
        raise SearchQueryError(f"검색어는 {Q_MIN}자에서 {Q_MAX}자까지 적어 주세요.")
    return q


def like_pattern(q: str) -> str:
    """LIKE 의 특수 글자(`\\`, `%`, `_`)를 `\\` 로 막고 앞뒤에 `%` — 사람이 적은 글자 그대로 찾는다."""
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
