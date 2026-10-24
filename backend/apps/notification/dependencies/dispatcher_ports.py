"""디스패처가 쓰는 허브 포트 구현의 공장 자리 — 요청 밖이라 FastAPI 의 DI 자리(dependency_overrides)를 못 쓴다.

main.py 가 configure_dispatcher_ports 로 tenancy·customer·visit 의 프로바이더를 꽂는다. 이 모듈은 다른 스포크를 모른다.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


@dataclass(frozen=True)
class DispatcherPorts:
    shop_profile: Callable[[AsyncSession], ShopProfilePort]
    customer_directory: Callable[[AsyncSession], CustomerDirectoryPort]
    visit_ledger: Callable[[AsyncSession], VisitLedgerPort]


_ports: DispatcherPorts | None = None


def configure_dispatcher_ports(ports: DispatcherPorts) -> None:
    global _ports
    _ports = ports


def dispatcher_ports() -> DispatcherPorts:
    if _ports is None:
        raise RuntimeError("디스패처의 허브 포트 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
    return _ports
