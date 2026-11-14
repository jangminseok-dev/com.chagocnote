"""허브 포트 자리 — search 가 요청 안에서 쓰는, 다른 스포크가 구현한 포트(결과 줄의 이름·사진).

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
요청 밖(색인기)의 포트는 indexer_ports.py 의 공장 자리다.
"""
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_customer_directory() -> CustomerDirectoryPort:
    raise RuntimeError("CustomerDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_visit_ledger() -> VisitLedgerPort:
    raise RuntimeError("VisitLedgerPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_media_library() -> MediaLibraryPort:
    raise RuntimeError("MediaLibraryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
