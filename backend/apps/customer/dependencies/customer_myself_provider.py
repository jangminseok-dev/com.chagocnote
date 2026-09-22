from __future__ import annotations

from customer.adapter.outbound.log_customer_myself_record_adapter import (
    LogCustomerMyselfRecordAdapter,
)
from customer.app.ports.input.customer_myself_use_case import CustomerMyselfUseCase
from customer.app.use_cases.customer_myself_interactor import CustomerMyselfInteractor


def get_customer_myself_use_case() -> CustomerMyselfUseCase:
    return CustomerMyselfInteractor(record=LogCustomerMyselfRecordAdapter())
