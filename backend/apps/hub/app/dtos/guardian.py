from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportLinkTarget:
    """알림장 토큰이 가리키는 매장과 고객. live 는 공개 알림장의 '열림'과 같은 뜻이다
    (끊음·기간 지남·매장 정지·폐업·익명화·기록 없음이면 False)."""

    shop_id: int
    customer_id: int
    live: bool


@dataclass(frozen=True)
class GuardianContext:
    """보호자로서의 요청 컨텍스트 — 그 계정의 살아 있는 연결 하나. `ShopContext` 의 보호자 쪽 짝이다.

    보호자용 읽기는 이 값의 shop_id·customer_id 로만 범위를 정한다(경로의 link_id 를 계정으로 확인한 결과다).
    """

    link_id: int
    user_id: int
    shop_id: int
    customer_id: int
