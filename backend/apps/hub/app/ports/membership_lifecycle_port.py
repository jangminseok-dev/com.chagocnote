from __future__ import annotations

from abc import ABC, abstractmethod


class MembershipLifecyclePort(ABC):
    """구현: tenancy. 사용: auth (회원 탈퇴)."""

    @abstractmethod
    async def apply_withdrawal(self, user_id: int, close_sole_owned: bool) -> None:
        """탈퇴하는 유저의 모든 소속을 해제한다. 부르는 쪽과 같은 트랜잭션 안에서 돈다.

        혼자 사장인 매장에 다른 멤버가 있으면 막고, 멤버가 본인뿐이면 close_sole_owned 가 참일 때만
        매장을 닫고 진행한다. 막힐 때는 구현 쪽 도메인 오류를 던진다 — 부르는 쪽의 트랜잭션이 통째로
        되돌아가므로 아무것도 바뀌지 않는다. 미리 조회하는 메서드를 따로 두지 않는 이유는, 조회와 적용
        사이에 다른 요청이 사장 수를 바꿀 수 있어서다.
        """
