from __future__ import annotations

from customer.app.dtos.set_pet_grooming_cycle_dto import SetPetGroomingCycleCommand
from customer.app.ports.input.set_pet_grooming_cycle_use_case import SetPetGroomingCycleUseCase
from customer.app.ports.output.pet_repository import PetRepository


class SetPetGroomingCycleInteractor(SetPetGroomingCycleUseCase):
    """그 아이의 미용 주기를 직접 정하거나 지운다(⑬ 설계 3.2). 고객 행부터 잠근다(동의 쓰기와 같다).
    누가 정했는지는 남기지 않는다 — 판단이 아니라 숫자다. 계산은 visit 이 읽을 때 한다."""

    def __init__(self, pets: PetRepository) -> None:
        self._pets = pets

    async def set_pet_grooming_cycle(self, command: SetPetGroomingCycleCommand) -> None:
        await self._pets.lock_owner(command.ctx, command.pet_id)   # 이 매장의 아이가 아니면 404
        await self._pets.set_grooming_cycle(command.ctx, command.pet_id, command.weeks)
