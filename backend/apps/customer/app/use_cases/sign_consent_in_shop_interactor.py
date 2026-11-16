from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from customer.app.dtos.sign_consent_in_shop_dto import SignConsentInShopCommand
from customer.app.ports.input.sign_consent_in_shop_use_case import SignConsentInShopUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_signer import SigningInput, sign
from customer.domain.entities.consent import ConsentPolicy
from customer.domain.errors import CustomerInputError


class SignConsentInShopInteractor(SignConsentInShopUseCase):
    """매장에 와 있는 보호자가 사장의 폰에서 서명한다(⑪ 설계 3.3)."""

    def __init__(
        self, pets: PetRepository, signatures: ConsentSignatureRepository, forms: ConsentFormRepository,
        today: Callable[[], date], now: Callable[[], datetime], policy: ConsentPolicy,
    ) -> None:
        self._pets = pets
        self._signatures = signatures
        self._forms = forms
        self._today = today
        self._now = now
        self._policy = policy

    async def sign_consent_in_shop(self, command: SignConsentInShopCommand) -> int:
        ctx = command.ctx
        if not command.pet_ids:
            raise CustomerInputError("아이를 하나 이상 골라 주세요.")
        await self._pets.lock_owner(ctx, min(command.pet_ids))
        return await sign(
            ctx,
            SigningInput(
                pet_ids=command.pet_ids, doc_digest=command.doc_digest, signer_name=command.signer_name,
                signature_png=command.signature_png, channel="in_shop", form_id=None, by_member_id=ctx.member_id,
                for_date=command.for_date,
            ),
            self._now(), self._today(), self._policy,
            pets=self._pets, signatures=self._signatures, forms=self._forms,
        )
