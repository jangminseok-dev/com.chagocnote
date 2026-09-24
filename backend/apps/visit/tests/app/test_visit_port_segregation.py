"""visits 표의 리포지토리 포트 여섯 — 인터페이스 분리를 구조로 고정한다.

손으로 관리하는 목록 대신 인터랙터 생성자의 타입 힌트를 읽는다. 조회 유스케이스가 쓰기 포트를 받게 되거나,
한 메서드가 두 포트에 들어가면 여기서 걸린다.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import get_type_hints

import visit.app.use_cases as use_cases
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.tests.helpers.fakes import FakeVisits

PORTS = (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
         VisitBoardRepository, VisitFeedRepository)


def _interactors():
    for info in pkgutil.iter_modules(use_cases.__path__):
        module = importlib.import_module(f"{use_cases.__name__}.{info.name}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if name.endswith("Interactor") and cls.__module__ == module.__name__:
                yield cls


def _ports_taken(cls) -> list[type]:
    """생성자 인자의 타입 가운데 방문 포트인 것. 모듈이 `from __future__ import annotations` 라 문자열을 풀어 읽는다."""
    hints = get_type_hints(cls.__init__)
    return [hint for name, hint in hints.items() if name != "return" and hint in PORTS]


def test_pg_구현은_여섯_포트를_다_낸다():
    assert all(issubclass(VisitPgRepository, port) for port in PORTS)
    missing = sorted(set(VisitPgRepository.__abstractmethods__))
    assert missing == []


def test_스텁도_여섯_포트의_메서드를_다_가진다():
    for port in PORTS:
        for name in port.__abstractmethods__:
            assert callable(getattr(FakeVisits, name, None)), f"FakeVisits 에 {port.__name__}.{name} 이 없다"


def test_쓰기_포트는_쓰는_유스케이스_넷만_받는다():
    writers = sorted(cls.__name__ for cls in _interactors() if VisitWriteRepository in _ports_taken(cls))
    assert writers == [
        "RegisterVisitInteractor", "RescheduleVisitsInteractor", "TransitionVisitsInteractor",
        "UpdateVisitInteractor",
    ]


def test_같은_포트를_두_번_받는_인터랙터는_없다():
    for cls in _interactors():
        taken = _ports_taken(cls)
        assert len(taken) == len(set(taken)), cls.__name__


def test_포트끼리_메서드가_겹치지_않는다():
    """찾기·잠금은 쓰기가 상속하므로 그 둘만 겹친다."""
    own = {port: set(port.__dict__) & port.__abstractmethods__ for port in PORTS}
    for first in PORTS:
        for second in PORTS:
            if first is not second:
                assert own[first].isdisjoint(own[second]), (first.__name__, second.__name__)
