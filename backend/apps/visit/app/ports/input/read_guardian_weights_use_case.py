from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.guardian_report_dto import GuardianWeightView, ReadGuardianWeightsQuery


class ReadGuardianWeightsUseCase(ABC):
    @abstractmethod
    async def read_weights(self, query: ReadGuardianWeightsQuery) -> list[GuardianWeightView]: ...
