"""공개 서류의 요청을 종류를 가리지 않고 찾는다 — 동의서와 문진표가 같은 토큰·같은 주소(`/f/…`)를 쓴다."""
from __future__ import annotations

from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.intake_form_repository import IntakeFormRepository
from customer.domain.entities.consent_form import ConsentForm
from customer.domain.entities.intake import IntakeForm


class PublicForms:
    """`open_form` 이 쓰는 모양(`find_public`)만 갖는다."""

    def __init__(self, consents: ConsentFormRepository, intakes: IntakeFormRepository) -> None:
        self._consents = consents
        self._intakes = intakes

    async def find_public(self, public_id: bytes) -> ConsentForm | IntakeForm | None:
        return await self._consents.find_public(public_id) or await self._intakes.find_public(public_id)
