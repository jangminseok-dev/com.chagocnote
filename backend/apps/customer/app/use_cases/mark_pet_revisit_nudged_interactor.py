from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.mark_pet_revisit_nudged_dto import MarkPetRevisitNudgedCommand
from customer.app.ports.input.mark_pet_revisit_nudged_use_case import MarkPetRevisitNudgedUseCase
from customer.app.ports.output.pet_repository import PetRepository


class MarkPetRevisitNudgedInteractor(MarkPetRevisitNudgedUseCase):
    """안내한 날을 오늘로 적는다(⑬ 설계 3.3). 보냈는지는 모른다 — 공유 시트는 알려 주지 않는다."""

    def __init__(self, pets: PetRepository, today: Callable[[], date]) -> None:
        self._pets = pets
        self._today = today

    async def mark_pet_revisit_nudged(self, command: MarkPetRevisitNudgedCommand) -> None:
        await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.set_revisit_nudged(command.ctx, command.pet_id, self._today())
