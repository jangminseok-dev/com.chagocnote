from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from visit.app.dtos.get_sales_summary_dto import SalesSummaryView


class PetCardSchema(BaseModel):
    """화면에 보일 아이. 익명화한 고객의 아이와 지운 아이는 이 모양으로 나오지 않는다."""

    pet_id: int
    name: str
    photo_url: str | None       # 프로필 사진 썸네일 — 없으면 빈 사진 칸


class SalesPeriodSchema(BaseModel):
    start: date
    end: date                   # 끝날(포함)
    elapsed_end: date | None    # 지나간 마지막 날. 아직 오지 않은 기간이면 null


class SalesCompareWindowSchema(BaseModel):
    start: date
    end: date
    revenue: int


class SalesCompareSchema(BaseModel):
    previous: SalesCompareWindowSchema | None
    year_ago: SalesCompareWindowSchema | None


class SalesGoalInSummarySchema(BaseModel):
    monthly_amount: int


class SalesPetsSchema(BaseModel):
    count: int
    new_count: int
    returning_count: int
    faces: list[PetCardSchema]
    new: list[PetCardSchema]
    returning: list[PetCardSchema]


class SalesBucketSchema(BaseModel):
    key: str                    # YYYY-MM-DD 또는 YYYY-MM
    revenue: int
    visit_count: int
    future: bool
    pets: list[PetCardSchema]


class SalesPaymentSchema(BaseModel):
    method: Literal["card", "cash", "transfer", "none"]
    amount: int


class SalesMenuSchema(BaseModel):
    menu_id: int | None         # 조정 줄이면 null
    name: str
    amount: int                 # 조정은 음수일 수 있다
    count: int
    pet: PetCardSchema | None


class SalesRegularSchema(BaseModel):
    pet: PetCardSchema
    visit_count: int


class SalesBookingsSchema(BaseModel):
    remaining: int | None
    expected_amount: int | None
    no_show: int
    canceled: int


class SalesReportSchema(BaseModel):
    completed: int
    sent: int
    opened: int


class SalesSummarySchema(BaseModel):
    """매출 탭 한 화면. 금액은 원, 날짜는 매장 시간대다."""

    span: Literal["day", "week", "month", "year"]
    period: SalesPeriodSchema
    revenue: int
    visit_count: int
    priced_count: int
    average: int | None
    compare: SalesCompareSchema
    goal: SalesGoalInSummarySchema | None
    pets: SalesPetsSchema
    buckets: list[SalesBucketSchema]
    payments: list[SalesPaymentSchema]
    menus: list[SalesMenuSchema]
    regulars: list[SalesRegularSchema]
    bookings: SalesBookingsSchema
    weekdays: list[int] | None
    report: SalesReportSchema | None
    unrecorded_count: int
    due_pet_count: int

    @classmethod
    def of(cls, view: SalesSummaryView) -> SalesSummarySchema:
        return cls.model_validate(view, from_attributes=True)
