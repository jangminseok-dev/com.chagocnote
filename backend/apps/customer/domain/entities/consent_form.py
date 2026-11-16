"""서류 요청과 서명 기록(⑪ 설계 5.2)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ConsentForm:
    """보호자에게 보낸 동의서 링크 하나. 토큰은 저장하지 않는다 — public_id 와 서버 키로 그때마다 계산한다."""

    id: int
    shop_id: int
    public_id: bytes
    customer_id: int
    pet_ids: tuple[int, ...]              # 오름차순
    expires_at: datetime
    revoked_at: datetime | None
    submitted_at: datetime | None
    created_by_member_id: int
    created_at: datetime
    for_date: date | None = None          # 문서를 조립하는 기준일(예약 날). 없으면 여는 날

    def is_live(self, now: datetime) -> bool:
        """끊지 않았고, 내지 않았고, 기간 안이다."""
        return self.revoked_at is None and self.submitted_at is None and now < self.expires_at

    def is_closed(self, now: datetime) -> bool:
        """끊었거나 기간이 지났다. 낸 요청은 닫힌 것이 아니다 — "보냈어요"를 보여야 한다.

        다만 낸 뒤에 고객을 익명화하면 끊긴다(revoked_at) — 그때는 낸 요청도 닫힌 것이다."""
        return self.revoked_at is not None or (self.submitted_at is None and now >= self.expires_at)


@dataclass(frozen=True)
class SignedPart:
    part: str
    text_source: str      # default | shop
    text_version: int


@dataclass(frozen=True)
class NewSignaturePet:
    pet_id: int
    shown_pet_name: str
    parts: tuple[SignedPart, ...]
    condition_labels: tuple[str, ...]


@dataclass(frozen=True)
class NewSignature:
    """저장할 서명 한 번. 그림과 적은 이름은 로그에 남기지 않는다."""

    customer_id: int
    form_id: int | None
    channel: str          # link | in_shop
    signer_name: str
    signature_png: bytes
    signed_at: datetime
    by_member_id: int
    pets: tuple[NewSignaturePet, ...]


@dataclass(frozen=True)
class SignatureBrief:
    signature_id: int
    signed_at: datetime
    channel: str
    signer_name: str
    parts: tuple[str, ...]            # 그 아이에 대해 읽은 토막


@dataclass(frozen=True)
class SignaturePetDetail:
    pet_id: int | None
    shown_pet_name: str
    condition_labels: tuple[str, ...]
    parts: tuple[SignedPart, ...]


@dataclass(frozen=True)
class SignatureDetail:
    signature_id: int
    signed_at: datetime
    channel: str
    signer_name: str
    by_member_id: int
    pets: tuple[SignaturePetDetail, ...]
