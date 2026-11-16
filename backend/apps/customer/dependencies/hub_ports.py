"""허브 포트 자리 — customer 가 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.guardian_lifecycle_port import GuardianLifecyclePort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.search_index_port import SearchIndexPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_visit_ledger() -> VisitLedgerPort:
    raise RuntimeError("VisitLedgerPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_media_library() -> MediaLibraryPort:
    raise RuntimeError("MediaLibraryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_guardian_lifecycle() -> GuardianLifecyclePort:
    raise RuntimeError("GuardianLifecyclePort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_domain_events() -> DomainEventPort:
    raise RuntimeError("DomainEventPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_search_index() -> SearchIndexPort:
    raise RuntimeError("SearchIndexPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_shop_profile() -> ShopProfilePort:
    raise RuntimeError("ShopProfilePort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")

