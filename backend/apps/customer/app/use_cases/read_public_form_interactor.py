from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from customer.app.dtos.public_form_dto import PublicFormView, ReadPublicFormQuery
from customer.app.ports.input.read_public_form_use_case import ReadPublicFormUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_reader import read_document
from customer.app.services.public_form_gate import open_form
from customer.app.use_cases.get_consent_document_interactor import document_view
from customer.domain.entities.consent import ConsentPolicy
from customer.domain.errors import CustomerInputError, FormClosedError, PetNotFoundError
from hub.app.dtos.shop_context import public_context
from hub.app.ports.public_limiter_port import PublicLimiterPort
from hub.app.ports.shop_profile_port import ShopProfilePort


class ReadPublicFormInteractor(ReadPublicFormUseCase):
    """보호자가 링크로 동의서를 읽는다. 로그인이 없다 — 토큰의 서명이 곧 범위다. 읽기만 하므로 잠그지 않는다.

    문안은 열 때 조립한다 — 보낸 뒤 지병이 더해졌으면 더해진 것을 읽는다.
    """

    def __init__(
        self, forms: ConsentFormRepository, pets: PetRepository, signatures: ConsentSignatureRepository,
        shops: ShopProfilePort, limiter: PublicLimiterPort, now: Callable[[], datetime], policy: ConsentPolicy,
        link_key: bytes,
    ) -> None:
        self._forms = forms
        self._pets = pets
        self._signatures = signatures
        self._shops = shops
        self._limiter = limiter
        self._now = now
        self._policy = policy
        self._link_key = link_key

    async def read_public_form(self, query: ReadPublicFormQuery) -> PublicFormView:
        now = self._now()
        form, shop = await open_form(
            query.token, query.client, now, link_key=self._link_key, forms=self._forms, shops=self._shops,
            limiter=self._limiter,
        )
        ctx = public_context(shop)
        zone = ZoneInfo(ctx.timezone)
        if form.submitted_at is not None:
            return PublicFormView(shop.name, None, form.submitted_at.astimezone(zone).date())
        try:
            doc = await read_document(
                ctx, form.pet_ids, now.astimezone(zone).date(), self._policy,
                pets=self._pets, signatures=self._signatures)
        except (PetNotFoundError, CustomerInputError):
            # 익명화한 고객의 요청이거나 담은 아이가 없다 — 닫힌 것으로 읽힌다.
            raise FormClosedError("닫힌 서류입니다.") from None
        if not doc.pets:
            return PublicFormView(shop.name, None, None)     # 그 사이 매장에서 받았다
        return PublicFormView(shop.name, document_view(doc), None)
