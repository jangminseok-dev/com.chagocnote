"""다른 스포크가 구현한 허브 포트의 자리. 진입점(main.py)이 구현을 꽂는다 — 여기서 다른 스포크를 import 하지 않는다."""
from __future__ import annotations

from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
from hub.app.ports.report_link_port import ReportLinkPort
from hub.app.ports.shop_profile_port import ShopProfilePort


def get_report_link() -> ReportLinkPort:
    raise RuntimeError("ReportLinkPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_active_user_guard() -> ActiveUserGuardPort:
    raise RuntimeError("ActiveUserGuardPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_shop_profile() -> ShopProfilePort:
    raise RuntimeError("ShopProfilePort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
