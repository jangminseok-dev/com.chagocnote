from __future__ import annotations

from core.database import DbSession
from customer.app.use_cases.customer_search_source_interactor import CustomerSearchSourceInteractor
from customer.dependencies.customer_wiring import build_customer_repository, build_pet_repository
from hub.app.ports.search_source_port import SearchSourcePort


def get_customer_search_source_use_case(db: DbSession) -> SearchSourcePort:
    """허브 포트 SearchSourcePort(scope "pet"·"customer")의 구현 — main.py 가 색인기의 공장 자리에 꽂는다."""
    return CustomerSearchSourceInteractor(customers=build_customer_repository(db), pets=build_pet_repository(db))
