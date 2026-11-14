"""색인기가 쓰는 허브 포트 구현의 공장 자리 — 요청 밖이라 FastAPI 의 DI 자리(dependency_overrides)를 못 쓴다.

main.py 가 configure_indexer_ports 로 tenancy·customer·visit 의 프로바이더를 꽂는다. 이 모듈은 다른 스포크를 모른다.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.search_source_port import SearchSourcePort
from hub.app.ports.shop_profile_port import ShopProfilePort


@dataclass(frozen=True)
class IndexerPorts:
    shop_profile: Callable[[AsyncSession], ShopProfilePort]
    customer_directory: Callable[[AsyncSession], CustomerDirectoryPort]
    visit_source: Callable[[AsyncSession], SearchSourcePort]       # scope "visit"
    customer_source: Callable[[AsyncSession], SearchSourcePort]    # scope "pet"·"customer"


_ports: IndexerPorts | None = None


def configure_indexer_ports(ports: IndexerPorts) -> None:
    global _ports
    _ports = ports


def indexer_ports() -> IndexerPorts:
    if _ports is None:
        raise RuntimeError("색인기의 허브 포트 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
    return _ports
