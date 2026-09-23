from __future__ import annotations

from collections.abc import Callable
from datetime import date
from zoneinfo import ZoneInfo

from customer.app.dtos.customer_view_dto import CustomerOverviewView, UpcomingVisitView
from customer.app.dtos.get_customer_dto import GetCustomerQuery
from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail
from hub.app.ports.visit_ledger_port import VisitLedgerPort

UPCOMING_LIMIT = 3


class GetCustomerInteractor(GetCustomerUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, ledger: VisitLedgerPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._ledger = ledger
        self._today = today

    async def get_customer(self, query: GetCustomerQuery) -> CustomerOverviewView:
        ctx = query.ctx
        detail = await read_customer_detail(ctx, query.customer_id, self._customers, self._pets, self._today())
        names = {pet.pet_id: pet.name for pet in detail.pets}
        zone = ZoneInfo(ctx.timezone)
        upcoming = await self._ledger.upcoming_for_customer(ctx, query.customer_id, UPCOMING_LIMIT)
        return CustomerOverviewView(
            customer=detail.customer,
            pets=detail.pets,
            no_show_count=await self._ledger.no_show_count(ctx, query.customer_id),
            upcoming_visits=[
                UpcomingVisitView(visit_id=u.visit_id, pet_id=u.pet_id, pet_name=names.get(u.pet_id),
                                  starts_at=u.starts_at.astimezone(zone))
                for u in upcoming
            ],
        )
