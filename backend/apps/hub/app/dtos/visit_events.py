from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class VisitEvent:
    """visit 이 발행하는 사실. 구독자는 같은 트랜잭션에서 돈다(설계 5.1)."""

    ctx: ShopContext          # 발행한 요청의 매장 컨텍스트 — 구독자가 포트를 부를 때 그대로 쓴다
    visit_id: int
    customer_id: int
    pet_id: int | None
    starts_at: datetime       # UTC
    occurred_at: datetime     # UTC, 발행 시각(인터랙터의 now)


@dataclass(frozen=True)
class VisitReserved(VisitEvent):
    revived: bool = False     # 되돌리기로 다시 예약됨이 된 경우 True(접수 안내는 보내지 않고 리마인드만 다시 만든다)


@dataclass(frozen=True)
class VisitRescheduled(VisitEvent):
    previous_starts_at: datetime


@dataclass(frozen=True)
class VisitCanceled(VisitEvent):
    reason: str               # "customer_request" | "shop_reason" (visit.domain.entities.visit.CANCEL_REASONS 와 같은 값)


@dataclass(frozen=True)
class VisitClosed(VisitEvent):
    outcome: str              # "completed" | "no_show"
    previous_completed_at: datetime | None   # 완료일 때 같은 아이(보호자만이면 보호자만 방문)의 앞선 완료 방문 시작 시각. 노쇼는 None


@dataclass(frozen=True)
class VisitReportIssued(VisitEvent):
    url: str                  # 알림장 주소(토큰이 들어 있다 — 로그에 찍지 않는다)
    expires_at: datetime | None
