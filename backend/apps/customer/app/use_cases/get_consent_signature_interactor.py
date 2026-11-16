from __future__ import annotations

from customer.app.dtos.consent_view_dto import SignatureDetailView, SignaturePetView, SignedPartView
from customer.app.dtos.get_consent_signature_dto import GetConsentSignatureQuery
from customer.app.ports.input.get_consent_signature_use_case import GetConsentSignatureUseCase
from customer.app.ports.output.consent_signature_repository import ConsentSignatureRepository
from customer.domain.entities.consent_form import SignedPart
from customer.domain.services.consent_text import default_body


def _body(part: SignedPart) -> str:
    """서명한 그 판의 글자. 매장이 고친 글(shop)은 ⑪-B 가 더한다 — 그 전에는 기본 글만 있다."""
    return default_body(part.part, part.text_version)


class GetConsentSignatureInteractor(GetConsentSignatureUseCase):
    """서명 한 장 — 그때 읽은 글과 보인 사실 그대로."""

    def __init__(self, signatures: ConsentSignatureRepository) -> None:
        self._signatures = signatures

    async def get_consent_signature(self, query: GetConsentSignatureQuery) -> SignatureDetailView:
        detail = await self._signatures.get(query.ctx, query.signature_id)
        return SignatureDetailView(
            signature_id=detail.signature_id, signed_at=detail.signed_at, channel=detail.channel,
            signer_name=detail.signer_name, by_member_id=detail.by_member_id,
            pets=tuple(
                SignaturePetView(
                    pet_id=pet.pet_id, shown_name=pet.shown_pet_name, conditions=pet.condition_labels,
                    parts=tuple(SignedPartView(part.part, _body(part)) for part in pet.parts),
                )
                for pet in detail.pets
            ),
        )
