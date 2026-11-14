from __future__ import annotations

SNIPPET_MAX = 80
_LEAD = 20       # 걸린 말 앞에 보여 줄 글자 수
_ELLIPSIS = "…"


def snippet(body: str, q: str) -> str:
    """결과 줄에 보일 한 토막 — 줄바꿈과 겹친 공백을 빈칸 하나로 줄이고 80자까지. 검색어가 글에 있으면
    (대소문자 없이) 그 자리가 들게 자르고, 없으면(뜻으로 걸렸다) 앞에서부터. 잘린 쪽에 말줄임표를 붙인다."""
    text = " ".join(body.split())
    if len(text) <= SNIPPET_MAX:
        return text
    at = text.casefold().find(q.casefold())
    start = 0 if at < 0 else max(0, min(at - _LEAD, len(text) - SNIPPET_MAX))
    end = start + SNIPPET_MAX
    return (_ELLIPSIS if start > 0 else "") + text[start:end] + (_ELLIPSIS if end < len(text) else "")
