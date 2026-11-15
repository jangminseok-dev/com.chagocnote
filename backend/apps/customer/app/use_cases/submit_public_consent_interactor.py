from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from customer.app.dtos.public_form_dto import SubmitPublicConsentCommand
from customer.app.ports.input.submit_public_consent_use_case import SubmitPublicConsentUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_signer import SigningInput, sign
from customer.app.services.public_form_gate import open_form
from customer.domain.entities.consent import ConsentPolicy
from customer.domain.errors import (
    CustomerNotFoundError, FormClosedError, PetNotFoundError, TooManyFormRequestsError,
)
from hub.app.dtos.shop_context import public_context
from hub.app.ports.public_limiter_port import PublicLimiterPort
from hub.app.ports.shop_profile_port import ShopProfilePort


class SubmitPublicConsentInteractor(SubmitPublicConsentUseCase):
    """보호자가 링크에서 서명해 보낸다. 로그인이 없다 — public_context 로 서류의 표와 동의 칸만 쓴다.

    잠금은 고객 행 → 서류 요청 행. 한 번 내면 닫힌다.
    """

    def __init__(
        self, forms: ConsentFormRepository, customers: CustomerRepository, pets: PetRepository,
        signatures: ConsentSignatureRepository, shops: ShopProfilePort, limiter: PublicLimiterPort,
        now: Callable[[], datetime], policy: ConsentPolicy, link_key: bytes,
    ) -> None:
        self._forms = forms
        self._customers = customers
        self._pets = pets
        self._signatures = signatures
        self._shops = shops
        self._limiter = limiter
        self._now = now
        self._policy = policy
        self._link_key = link_key

    async def submit_public_consent(self, command: SubmitPublicConsentCommand) -> None:
        now = self._now()
        found, shop = await open_form(
            command.token, command.client, now, link_key=self._link_key, forms=self._forms, shops=self._shops,
            limiter=self._limiter,
        )
        if not await self._limiter.allow_write(command.client):
            raise TooManyFormRequestsError("요청이 너무 잦습니다. 잠시 뒤에 다시 보내 주세요.")
        ctx = public_context(shop)
        try:
            await self._customers.lock_active(ctx, found.customer_id)
        except CustomerNotFoundError:
            raise FormClosedError("닫힌 서류입니다.") from None
        form = await self._forms.lock(found.id)
        # 잠금을 기다리는 사이 내거나 끊었을 수 있다 — 잠근 뒤의 값으로 다시 본다.
        if form is None or not form.is_live(now):
            raise FormClosedError("닫힌 서류입니다.")
        await self._forms.mark_submitted(form.id, now)
        try:
            await sign(
                ctx,
                SigningInput(
                    pet_ids=form.pet_ids, doc_digest=command.doc_digest, signer_name=command.signer_name,
                    signature_png=command.signature_png, channel="link", form_id=form.id,
                    by_member_id=form.created_by_member_id,     # 받은 멤버는 링크를 보낸 멤버다
                ),
                now, now.astimezone(ZoneInfo(ctx.timezone)).date(), self._policy,
                pets=self._pets, signatures=self._signatures, forms=self._forms,
            )
        except PetNotFoundError:
            raise FormClosedError("닫힌 서류입니다.") from None
