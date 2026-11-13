from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.guardian_report_dto import GuardianPetView, ListGuardianPetsQuery
from visit.app.ports.input.list_guardian_pets_use_case import ListGuardianPetsUseCase
from visit.app.ports.output.guardian_report_repository import GuardianReportRepository
from visit.app.services.guardian_scope import guardian_scope


class ListGuardianPetsInteractor(ListGuardianPetsUseCase):
    """보호자가 보는 아이들 — **알림장을 받은 적 있는 아이만**. 매장에 등록만 된 아이의 이름은 드러나지 않는다.
    무지개다리를 건넌 아이도 넣는다(지난 기록은 남는다)."""

    def __init__(
        self, reports: GuardianReportRepository, directory: CustomerDirectoryPort, shops: ShopProfilePort
    ) -> None:
        self._reports = reports
        self._directory = directory
        self._shops = shops

    async def list_pets(self, query: ListGuardianPetsQuery) -> list[GuardianPetView]:
        scope = await guardian_scope(query.guardian, self._shops)
        if scope is None:
            return []
        ctx, _ = scope
        pet_ids = await self._reports.pet_ids_with_reports(ctx, query.guardian.customer_id)
        pets = (await self._directory.briefs(ctx, [], pet_ids)).pets if pet_ids else {}
        return [GuardianPetView(pet_id=p, name=pets[p].name) for p in pet_ids if p in pets]
