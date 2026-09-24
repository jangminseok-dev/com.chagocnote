"""예상 소요 시간의 기본값 — 고른 메뉴의 기본 소요를 더하고, 없으면 매장 기본 소요.

메뉴의 기본 소요가 비어 있으면(None) 그 메뉴는 매장 기본 소요로 센다. 메뉴를 하나도 고르지 않았으면 매장 기본
소요다. 등록·수정 화면의 "미리 채움"과 서버의 기본값이 같은 규칙을 써야 하므로 도메인에 둔다.
"""
from __future__ import annotations

from collections.abc import Sequence

from visit.domain.entities.menu import Menu


def default_duration(menus: Sequence[Menu], shop_default_minutes: int) -> int:
    return sum(m.default_duration_minutes or shop_default_minutes for m in menus) or shop_default_minutes
