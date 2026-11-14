from __future__ import annotations

from core.database import DbSession
from hub.app.ports.search_index_port import SearchIndexPort
from search.app.use_cases.forget_customer_interactor import ForgetCustomerInteractor
from search.dependencies.search_wiring import build_document_repository, build_queue_repository
from search.domain.services.clock import utc_now


def get_forget_customer_use_case(db: DbSession) -> SearchIndexPort:
    """허브 포트 SearchIndexPort 의 구현 — main.py 가 customer 의 자리에 꽂는다. 요청의 세션(= 익명화의 트랜잭션)."""
    return ForgetCustomerInteractor(
        documents=build_document_repository(db), queue=build_queue_repository(db), now=utc_now,
    )
