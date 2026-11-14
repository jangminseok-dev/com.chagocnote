from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopContext:
    """매장 범위 요청의 컨텍스트 — 누가(member_id) 어느 매장(shop_id)에서 어떤 권한으로 행동하는가.

    매장 범위의 리포지토리 메서드는 이 값을 필수 첫 인자로 받는다.
    컨텍스트 없이는 조회할 수 없게 해서 다른 매장의 데이터가 섞이는 사고를 구조로 막는다.
    """

    shop_id: int
    member_id: int
    role: str
    permissions: frozenset[str]
    # 매장의 IANA 시간대. "오늘"과 하루의 경계를 이 시간대로 계산한다(③ 예약).
    # 기본값은 shops.timezone 의 기본값과 같다 — 매장 접근 확인(tenancy)은 언제나 DB 값을 채운다.
    timezone: str = "Asia/Seoul"


def system_context(shop_id: int, timezone: str = "Asia/Seoul") -> ShopContext:
    """요청 밖(알림 디스패처·검색 색인기·운영자 스크립트)에서 ShopContext 를 만드는 유일한 곳. 권한이 비어 있고
    허브 포트 읽기와 자기 스포크의 표 쓰기(알림 표·검색 표)에만 쓴다.

    멤버가 없어 member_id 는 0 이다. 시간대는 ShopProfilePort 에서 읽은 매장 값을 넣는다 — 시각 계산이 없는
    저장(status 바꾸기)만이면 기본값으로 둔다.
    """
    return ShopContext(shop_id=shop_id, member_id=0, role="system", permissions=frozenset(), timezone=timezone)
