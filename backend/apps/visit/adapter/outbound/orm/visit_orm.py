from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from visit.domain.state.visit_status import (
    ACTIVE_STATUSES,
    ALL_STATUSES,
    STARTED_STATUSES,
    status_list_sql,
)

_DURATION_RULE = "BETWEEN 10 AND 600 AND {col} % 10 = 0"
# 상태 이름을 여기 적지 않는다 — 도메인 표(visit_status)에서 만든다. 상태가 늘면 새 마이그레이션을 손으로 써야 한다 —
# tests/test_schema_drift.py 는 CHECK·부분 색인을 비교하지 않으므로, tests/integration/test_visit_status_schema.py 가
# 실제 DB 의 CHECK·부분 색인을 표와 대조해 알려 준다.
_STATUS_IN = "status IN (" + status_list_sql(ALL_STATUSES) + ")"
_ACTIVE_IN = "status IN (" + status_list_sql(ACTIVE_STATUSES) + ")"
_STARTED_IN = "status IN (" + status_list_sql(STARTED_STATUSES) + ")"


class VisitShopSettingsOrm(Base):
    """매장마다 한 줄. 이 행이 있다는 것이 곧 기본 메뉴를 넣었다는 뜻이다(설계 5.1)."""

    __tablename__ = "visit_shop_settings"
    __table_args__ = (
        CheckConstraint("opens_at < closes_at", name="ck_visit_shop_settings_hours"),
        CheckConstraint(
            "default_duration_minutes " + _DURATION_RULE.format(col="default_duration_minutes"),
            name="ck_visit_shop_settings_duration",
        ),
    )

    # tenancy 의 매장 ID. 스포크를 넘는 외래 키는 걸지 않는다.
    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)
    default_duration_minutes: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VisitWeeklyClosureOrm(Base):
    """매주 쉬는 요일 하나(월=0 … 일=6). 배열 칸 대신 행이다(1NF)."""

    __tablename__ = "visit_weekly_closures"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_visit_weekly_closures_weekday"),
    )

    shop_id: Mapped[int] = mapped_column(
        ForeignKey("visit_shop_settings.shop_id"), primary_key=True
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)


class VisitClosedDateOrm(Base):
    __tablename__ = "visit_closed_dates"

    shop_id: Mapped[int] = mapped_column(
        ForeignKey("visit_shop_settings.shop_id"), primary_key=True
    )
    # 칸 이름은 date 다. 속성 이름을 date 로 두면 주석의 date 형과 부딪혀 day 로 부른다.
    day: Mapped[date] = mapped_column("date", Date, primary_key=True)
    note: Mapped[str | None] = mapped_column(String(30))


class ServiceMenuOrm(Base):
    __tablename__ = "service_menus"
    __table_args__ = (
        # 보관한 메뉴는 이름이 겹쳐도 된다 — 같은 이름으로 다시 만들 수 있다.
        Index(
            "uq_service_menus_shop_name_active", "shop_id", "name",
            unique=True, postgresql_where=text("archived_at IS NULL"),
        ),
        CheckConstraint(
            "default_duration_minutes IS NULL OR default_duration_minutes "
            + _DURATION_RULE.format(col="default_duration_minutes"),
            name="ck_service_menus_duration",
        ),
        CheckConstraint("price IS NULL OR price BETWEEN 0 AND 100000000", name="ck_service_menus_price"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("visit_shop_settings.shop_id"), index=True)
    name: Mapped[str] = mapped_column(String(30))
    default_duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    sort_order: Mapped[int] = mapped_column(SmallInteger)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price: Mapped[int | None] = mapped_column(Integer)   # 정가(원). NULL 이면 가격 미정
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VisitOrm(Base):
    """반려동물 한 마리(pet_id 가 NULL 이면 보호자만)의 방문 하나."""

    __tablename__ = "visits"
    __table_args__ = (
        CheckConstraint(_STATUS_IN, name="ck_visits_status"),
        CheckConstraint(
            "duration_minutes " + _DURATION_RULE.format(col="duration_minutes"),
            name="ck_visits_duration",
        ),
        CheckConstraint(
            "cancel_reason IS NULL OR cancel_reason IN ('customer_request', 'shop_reason')",
            name="ck_visits_cancel_reason",
        ),
        # 상태가 원본이고, 시각·사유 칸은 그 상태일 때만 있다(설계 5.2).
        CheckConstraint(
            "(status = 'canceled') = (canceled_at IS NOT NULL) "
            "AND (status = 'canceled') = (cancel_reason IS NOT NULL)",
            name="ck_visits_canceled_fields",
        ),
        CheckConstraint(
            "(status = 'completed') = (completed_at IS NOT NULL)", name="ck_visits_completed_at"
        ),
        CheckConstraint("(" + _STARTED_IN + ") = (started_at IS NOT NULL)", name="ck_visits_started_at"),
        # 중복 예약 방지 — 저장을 두 번 눌러도 살아 있는 예약은 하나다(설계 V5).
        Index(
            "uq_visits_pet_start_active", "pet_id", "starts_at", unique=True,
            postgresql_where=text("pet_id IS NOT NULL AND " + _ACTIVE_IN),
        ),
        Index(
            "uq_visits_customer_start_active", "customer_id", "starts_at", unique=True,
            postgresql_where=text("pet_id IS NULL AND " + _ACTIVE_IN),
        ),
        Index("ix_visits_shop_starts_at", "shop_id", "starts_at"),
        Index("ix_visits_shop_customer", "shop_id", "customer_id"),
        Index("ix_visits_shop_pet", "shop_id", "pet_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 다른 스포크(tenancy·customer)의 ID — 외래 키 없이 색인만. 설계 5.3 의 역정규화.
    shop_id: Mapped[int] = mapped_column(BigInteger)
    customer_id: Mapped[int] = mapped_column(BigInteger)
    pet_id: Mapped[int | None] = mapped_column(BigInteger)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(String(20))
    memo: Mapped[str | None] = mapped_column(String(500))
    created_by_member_id: Mapped[int] = mapped_column(BigInteger)
    status_changed_by_member_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VisitMenuOrm(Base):
    __tablename__ = "visit_menus"

    visit_id: Mapped[int] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True
    )
    menu_id: Mapped[int] = mapped_column(ForeignKey("service_menus.id"), primary_key=True)
