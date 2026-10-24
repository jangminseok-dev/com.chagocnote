from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerContact:
    """알림을 보낼 때만 읽는 보호자 연락처. 익명화한 고객은 이 값이 없다(None)."""

    customer_id: int
    name: str
    phone: str              # 숫자만, 예: "01012345678"(customers.phone 의 저장 형식 그대로)
    marketing_consent: bool
