from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from customer.app.ports.input.update_customer_use_case import UpdateCustomerUseCase
from customer.app.use_cases.update_customer_interactor import UpdateCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.dependencies.hub_ports import get_domain_events
from customer.domain.services.pet_age import seoul_today
from hub.app.ports.domain_event_port import DomainEventPort


def get_update_customer_use_case(
    db: DbSession, events: DomainEventPort = Depends(get_domain_events),
) -> UpdateCustomerUseCase:
    return UpdateCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today, events=events,
    )
