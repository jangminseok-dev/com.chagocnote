"""보호자에게 나가는 알림장 응답(설계 6.3). 매장용 스키마를 쓰지 않고 칸을 하나하나 적는다.

내부 메모·결제 수단·예약 메모·보호자 이름·전화번호와 방문·고객·반려동물·미디어·매장의 ID 는 칸이 없다.
새 칸을 더하는 것은 공개 범위를 넓히는 일이다.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from visit.app.dtos.read_public_report_dto import PublicReportView
from visit.domain.value_objects.report_settings import ReportSettings

# 끊은 링크가 중간 캐시에 남지 않게, 검색 로봇이 담아 가지 않게.
PUBLIC_REPORT_HEADERS = {"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow"}


class _Public(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PublicMediaSchema(_Public):
    kind: str                 # photo · video
    phase: str                # before · after
    width: int
    height: int
    duration_seconds: int | None
    display_url: str          # 사진은 표시용, 영상은 원본(재생용)
    thumb_url: str            # 영상이면 포스터
    download_url: str


class PublicCoverSchema(_Public):
    url: str
    width: int
    height: int


class PublicMenuSchema(_Public):
    name: str
    amount: int | None = None        # 금액을 켰을 때만 있다


class PublicShopSchema(_Public):
    name: str
    phone: str | None
    address: str | None


class PublicReportSchema(_Public):
    pet_name: str | None             # 보호자만의 방문이면 null
    visit_date: date                 # 매장 시간대의 날짜
    care_note: str | None
    media: list[PublicMediaSchema]   # 후 → 전, 그 안에서 순서대로. 뺀 것은 없다
    cover: PublicCoverSchema | None
    menus: list[PublicMenuSchema] | None = None     # 메뉴를 켰을 때만 있다
    total_amount: int | None = None                 # 금액을 켰을 때만 있다
    weight_kg: float | None = None                  # 몸무게를 켰을 때만 있다
    shop: PublicShopSchema | None = None            # 매장 정보를 켰을 때만 있다
    review_url: str | None = None                   # 리뷰 남기기 줄(⑫) — 매장이 주소를 넣었고 이 알림장이 빼지 않았을 때만 있다
    review_text: str | None = None                  # 그 줄의 문구(매장의 글이거나 기본 문구)
    expires_at: datetime | None      # 매장 시간대. null 이면 기간이 없다

    @classmethod
    def body(cls, view: PublicReportView) -> dict:
        """응답 본문. 끈 항목은 null 이 아니라 칸이 없고, 켰지만 값이 없는 칸은 null 이다."""
        report = view.report
        schema = cls(
            pet_name=report.pet_name, visit_date=report.visit_date, care_note=report.care_note,
            media=list(report.media), cover=report.cover, menus=report.menus, total_amount=report.total_amount,
            weight_kg=report.weight_kg, shop=report.shop, expires_at=view.expires_at,
            review_url=report.review_url, review_text=report.review_text,
        )
        off = _turned_off(report.settings)
        if report.review_url is None:
            off |= {"review_url": True, "review_text": True}   # 빈 줄이 나가지 않는다 — 칸째 없다
        return schema.model_dump(mode="json", exclude=off)


def _turned_off(settings: ReportSettings) -> dict:
    """매장이 끈 칸 — model_dump 의 exclude 모양."""
    off: dict = {}
    if not settings.show_menus:
        off["menus"] = True
    elif not settings.show_amount:
        off["menus"] = {"__all__": {"amount"}}
    if not settings.show_amount:
        off["total_amount"] = True
    if not settings.show_weight:
        off["weight_kg"] = True
    if not settings.show_shop_info:
        off["shop"] = True
    return off
