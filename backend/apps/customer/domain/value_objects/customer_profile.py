from __future__ import annotations

from dataclasses import dataclass

from customer.domain.services.phone_number import normalize_phone


@dataclass(frozen=True)
class CustomerProfile:
    """검증을 마친 보호자 정보. 전화번호는 숫자만이다."""

    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    memo: str | None

    @classmethod
    def create(
        cls, *, name: str, phone: str, phone_alt: str | None, marketing_consent: bool,
        memo: str | None,
    ) -> CustomerProfile:
        return cls(
            name=name,
            phone=normalize_phone(phone),
            phone_alt=normalize_phone(phone_alt) if phone_alt is not None else None,
            marketing_consent=marketing_consent,
            memo=memo,
        )
