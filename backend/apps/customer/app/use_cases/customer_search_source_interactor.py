from __future__ import annotations

from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.search_documents import customer_documents, pet_documents
from customer.domain.errors import CustomerNotFoundError, PetNotFoundError
from hub.app.dtos.search_source import SourceDocument
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.search_source_port import SearchSourcePort


class CustomerSearchSourceInteractor(SearchSourcePort):
    """허브의 SearchSourcePort 구현 — scope "pet"·"customer" 만 답한다(HTTP 표면 없음). 색인기가 요청 밖에서 부른다.

    저장소가 살아 있는 이 매장의 고객(과 그 아이)만 돌려주므로, 익명화한 고객·지운 아이·다른 매장의 것은 빈 목록이다.
    잠그지 않는다."""

    def __init__(self, customers: CustomerRepository, pets: PetRepository) -> None:
        self._customers = customers
        self._pets = pets

    async def documents(self, ctx: ShopContext, scope: str, ref_id: int) -> list[SourceDocument]:
        try:
            if scope == "pet":
                return pet_documents(await self._pets.get(ctx, ref_id))
            if scope == "customer":
                return customer_documents(await self._customers.get_active(ctx, ref_id))
        except (PetNotFoundError, CustomerNotFoundError):
            return []
        return []
