from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class BuildSendBundleCommand:
    ctx: ShopContext
    visit_id: int


@dataclass(frozen=True)
class BundlePartView:
    """보호자에게 보낼 글의 토막 하나. kind 는 reservation·consent — 뒤의 묶음이 종류를 더한다."""

    kind: str
    text: str
