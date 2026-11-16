"""알림장을 보여 줄 모양 — 공개 조회와 매장의 미리보기가 함께 쓴다.

보호자 이름·전화번호, 내부 메모, 결제 수단, 예약 메모의 칸은 없다(설계 7.5 R6).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from visit.domain.value_objects.report_settings import ReportSettings


@dataclass(frozen=True)
class ReportMediaView:
    media_id: int            # 매장용 응답에만 나간다. 공개 응답에는 칸이 없다
    kind: str                # photo · video
    phase: str               # before · after
    hidden: bool             # 알림장에서 뺀 것 — 미리보기에만 담긴다
    width: int
    height: int
    duration_seconds: int | None
    display_url: str         # 사진은 표시용, 영상은 원본(재생용)
    thumb_url: str           # 영상이면 포스터
    download_url: str


@dataclass(frozen=True)
class ReportCoverView:
    url: str                 # 사진이면 표시용, 영상이면 포스터
    width: int
    height: int


@dataclass(frozen=True)
class ReportMenuView:
    name: str
    amount: int | None       # 금액을 끄면 None


@dataclass(frozen=True)
class ReportShopView:
    name: str
    phone: str | None
    address: str | None


@dataclass(frozen=True)
class ReportView:
    """끈 항목은 조립할 때 비운다(None) — 받는 쪽이 숨기는 것이 아니다(설계 7.5 R7)."""

    pet_name: str | None                      # 보호자만의 방문이거나 이름을 얻지 못하면 None
    visit_date: date                          # 방문 시작 시각의, 매장 시간대의 날짜
    care_note: str | None
    media: tuple[ReportMediaView, ...]        # 후 → 전, 그 안에서 순서대로
    cover: ReportCoverView | None             # 빼지 않은 것 가운데 대표
    menus: tuple[ReportMenuView, ...] | None  # 메뉴를 끄면 None
    total_amount: int | None                  # 금액을 켰을 때만
    weight_kg: Decimal | None                 # 몸무게를 켰을 때만
    shop: ReportShopView | None               # 매장 정보를 켰을 때만
    settings: ReportSettings                  # 공개 응답이 끈 항목의 칸을 아예 빼는 데 쓴다
    review_url: str | None = None             # 리뷰 남기기 줄(⑫) — 주소가 없거나 그 알림장이 뺐으면 None
    review_text: str | None = None            # 그 줄의 문구(기본 문구로 채워져 있다)


@dataclass(frozen=True)
class ReportLinkView:
    """링크의 상태. 살아 있는 링크가 없으면 status 만 none 이고 나머지는 None 이다."""

    status: str                # none · live
    url: str | None
    expires_at: datetime | None       # None 이면 기간이 없다
    first_viewed_at: datetime | None
    created_at: datetime | None       # 보낸 시각
    show_review: bool | None = None   # 이 알림장에 리뷰 줄을 넣는가(⑫) — 링크가 없으면 None

    def in_zone(self, zone: ZoneInfo) -> ReportLinkView:
        """시각을 매장 시간대로 바꾼 것 — 응답으로 내보내기 전에 부른다."""
        def local(moment: datetime | None) -> datetime | None:
            return moment.astimezone(zone) if moment is not None else None

        return replace(self, expires_at=local(self.expires_at), first_viewed_at=local(self.first_viewed_at),
                       created_at=local(self.created_at))
