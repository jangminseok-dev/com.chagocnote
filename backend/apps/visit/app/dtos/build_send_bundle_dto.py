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


@dataclass(frozen=True)
class SendBundleView:
    parts: list[BundlePartView]
    # 이 조립이 새로 만든 동의서 링크. 사장이 보내지 않고 닫으면 앱이 이것만 끊는다 — 보내지 않은 링크로
    # "보냈어요"가 뜨지 않게. 살아 있던 링크를 썼거나 링크가 없으면 None.
    created_form_id: int | None = None
