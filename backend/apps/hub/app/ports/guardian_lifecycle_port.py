from __future__ import annotations

from abc import ABC, abstractmethod


class GuardianLifecyclePort(ABC):
    """구현: guardian. 사용: auth (회원 탈퇴, 인증 프로세스), customer (고객 익명화)."""

    @abstractmethod
    async def end_for_user(self, user_id: int) -> int:
        """탈퇴하는 계정의 살아 있는 연결을 모두 끝낸다 — 고객 카드가 다른 계정으로 다시 이어질 수 있게.
        유저 행을 잠근 트랜잭션 안에서 부른다(잠금 순서: 유저 행 → 보호자 연결 행). 끝낸 수."""

    @abstractmethod
    async def end_for_customer(self, shop_id: int, customer_id: int) -> int:
        """익명화하는 고객 카드의 살아 있는 연결을 끝낸다. 고객 행을 잠근 트랜잭션 안에서 부른다
        (잠금 순서: 고객 행 → 보호자 연결 행). 끝낸 수."""
