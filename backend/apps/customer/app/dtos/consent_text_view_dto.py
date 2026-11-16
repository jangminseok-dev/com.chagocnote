from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsentTextView:
    """서류 설정에 보이는 토막 하나 — 지금 글과 기본 글."""

    part: str
    body: str
    edited: bool          # 매장이 고친 글인가
    default_body: str
