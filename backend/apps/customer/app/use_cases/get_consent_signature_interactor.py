from __future__ import annotations

from customer.app.dtos.consent_view_dto import SignatureDetailView, SignaturePetView, SignedPartView
from customer.app.dtos.get_consent_signature_dto import GetConsentSignatureQuery
from customer.app.ports.input.get_consent_signature_use_case import GetConsentSignatureUseCase
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.app.ports.output.consent_text_repository import ConsentTextRepository
from customer.domain.entities.consent_form import SignedPart
from customer.domain.services.consent_text import DEFAULT_VERSION, default_body
from hub.app.dtos.shop_context import ShopContext


class GetConsentSignatureInteractor(GetConsentSignatureUseCase):
    """서명 한 장 — 그때 읽은 글과 보인 사실 그대로."""

    def __init__(self, signatures: ConsentSignatureRepository, texts: ConsentTextRepository | None = None) -> None:
        self._signatures = signatures
        self._texts = texts

    async def _body(self, ctx: ShopContext, part: SignedPart) -> str:
        """서명한 그 판의 글자 — 매장이 그 뒤에 글을 고쳤어도 그때의 글이다."""
        if part.text_source == "shop" and self._texts is not None:
            body = await self._texts.body_of(ctx, part.part, part.text_version)
            if body is not None:
                return body
        return default_body(part.part, part.text_version if part.text_source == "default" else DEFAULT_VERSION)

    async def get_consent_signature(self, query: GetConsentSignatureQuery) -> SignatureDetailView:
        detail = await self._signatures.get(query.ctx, query.signature_id)
        bodies = {
            (part.part, part.text_source, part.text_version): await self._body(query.ctx, part)
            for pet in detail.pets for part in pet.parts
        }
        return SignatureDetailView(
            signature_id=detail.signature_id, signed_at=detail.signed_at, channel=detail.channel,
            signer_name=detail.signer_name, by_member_id=detail.by_member_id,
            pets=tuple(
                SignaturePetView(
                    pet_id=pet.pet_id, shown_name=pet.shown_pet_name, conditions=pet.condition_labels,
                    parts=tuple(SignedPartView(part.part, bodies[(part.part, part.text_source, part.text_version)]) for part in pet.parts),
                )
                for pet in detail.pets
            ),
        )
