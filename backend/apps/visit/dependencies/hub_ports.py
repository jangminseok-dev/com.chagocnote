"""허브 포트 자리 — visit 이 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort


def get_customer_directory() -> CustomerDirectoryPort:
    raise RuntimeError("CustomerDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_domain_events() -> DomainEventPort:
    raise RuntimeError("DomainEventPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_media_library() -> MediaLibraryPort:
    raise RuntimeError("MediaLibraryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_shop_profile() -> ShopProfilePort:
    raise RuntimeError("ShopProfilePort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
