from __future__ import annotations

from search.adapter.outbound.log_search_myself_record_adapter import (
    LogSearchMyselfRecordAdapter,
)
from search.app.ports.input.search_myself_use_case import SearchMyselfUseCase
from search.app.use_cases.search_myself_interactor import SearchMyselfInteractor


def get_search_myself_use_case() -> SearchMyselfUseCase:
    return SearchMyselfInteractor(record=LogSearchMyselfRecordAdapter())
