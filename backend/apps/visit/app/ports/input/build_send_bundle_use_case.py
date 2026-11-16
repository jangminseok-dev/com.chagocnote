from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.build_send_bundle_dto import BuildSendBundleCommand, SendBundleView


class BuildSendBundleUseCase(ABC):
    @abstractmethod
    async def build_send_bundle(self, command: BuildSendBundleCommand) -> SendBundleView: ...
