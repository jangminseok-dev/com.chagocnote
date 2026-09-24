"""허브 포트 자리 — customer 가 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_visit_ledger() -> VisitLedgerPort:
    raise RuntimeError("VisitLedgerPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


def get_media_library() -> MediaLibraryPort:
    raise RuntimeError("MediaLibraryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
