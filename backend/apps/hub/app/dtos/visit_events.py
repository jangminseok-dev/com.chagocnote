from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class VisitEvent:
    """visit 이 발행하는 사실. 구독자는 같은 트랜잭션에서 돈다(설계 5.1).

    하위 클래스마다 맨 끝에 `family_pet_ids: tuple[int, ...] = ()` 가 있다 — 이 명령이 함께 다룬 같은 보호자·같은
    시작 시각 방문들의 pet_id(None 은 뺀다, 자기 것 포함, 오름차순). 가족 묶음을 알림톡 한 통으로 묶는 데 쓴다.
    frozen dataclass 상속에서 기본값 칸은 필수 칸 뒤에 와야 해서 바탕 클래스가 아니라 하위 클래스 끝에 둔다.
    """

    ctx: ShopContext          # 발행한 요청의 매장 컨텍스트 — 구독자가 포트를 부를 때 그대로 쓴다
    visit_id: int
    customer_id: int
    pet_id: int | None
    starts_at: datetime       # UTC
    occurred_at: datetime     # UTC, 발행 시각(인터랙터의 now)


@dataclass(frozen=True)
class VisitReserved(VisitEvent):
    revived: bool = False     # 되돌리기로 다시 예약됨이 된 경우 True(접수 안내는 보내지 않고 리마인드만 다시 만든다)
    # ⑭ 한꺼번에 잡은 반복 예약의 둘째 회차부터 True — 접수 안내는 첫 회차 한 통, 나머지는 리마인드만.
    series_followup: bool = False
    family_pet_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class VisitRescheduled(VisitEvent):
    previous_starts_at: datetime
    family_pet_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class VisitCanceled(VisitEvent):
    reason: str               # "customer_request" | "shop_reason" (visit.domain.entities.visit.CANCEL_REASONS 와 같은 값)
    family_pet_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class VisitClosed(VisitEvent):
    outcome: str              # "completed" | "no_show"
    previous_completed_at: datetime | None   # 완료일 때 같은 아이(보호자만이면 보호자만 방문)의 앞선 완료 방문 시작 시각. 노쇼는 None
    # 아이의 미용 주기(⑬ 설계 3.4) — 다음 예약 제안의 주 수. cycle_weeks 는 직접 정한 값·계산한 값일 때만 있다.
    cycle_weeks: int | None = None
    cycle_source: str = "none"   # manual · computed · single · none
    default_cycle_weeks: int = 4   # 매장의 기본 간격 — 주기를 모를 때
    family_pet_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class VisitReportIssued(VisitEvent):
    url: str                  # 알림장 주소(토큰이 들어 있다 — 로그에 찍지 않는다)
    expires_at: datetime | None
    family_pet_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class VisitReportRevoked(VisitEvent):
    """알림장 링크를 끊었다 — 아직 안 나간 알림장 알림톡을 거둔다. 익명화가 끊는 링크는 이벤트가 없다(디스패처의
    anonymized 검사가 막는다)."""

    family_pet_ids: tuple[int, ...] = ()
