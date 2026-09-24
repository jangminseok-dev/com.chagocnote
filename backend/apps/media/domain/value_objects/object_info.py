from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectInfo:
    """저장소가 HEAD 로 알려 주는 객체의 실제 크기와 형식."""

    size_bytes: int
    content_type: str
