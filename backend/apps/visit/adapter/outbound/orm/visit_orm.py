from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
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
        CheckConstraint(
            "report_link_days IS NULL OR report_link_days IN (7, 30)",
            name="ck_visit_shop_settings_report_link_days",
        ),
        CheckConstraint(
            "sales_monthly_goal IS NULL OR sales_monthly_goal BETWEEN 1 AND 100000000",
            name="ck_visit_shop_settings_sales_goal",
        ),
    )

    # tenancy 의 매장 ID. 스포크를 넘는 외래 키는 걸지 않는다.
    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)
    default_duration_minutes: Mapped[int] = mapped_column(SmallInteger)
    # ⑤ 알림장 — 링크 기간(일, NULL 이면 무기한)과 보호자에게 보여 줄 항목.
    report_link_days: Mapped[int | None] = mapped_column(SmallInteger, server_default=text("30"))
    report_show_menus: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    report_show_shop_info: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    report_show_weight: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    report_show_amount: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # 알림장 끝의 리뷰 남기기 줄(0024, ⑫) — 주소가 없으면 줄이 없다, 문구가 없으면 기본 문구.
    report_review_url: Mapped[str | None] = mapped_column(String(300))
    report_review_text: Mapped[str | None] = mapped_column(String(60))
    # ⑧ 매출 — 월 목표 금액(원). NULL 이면 목표가 없다.
    sales_monthly_goal: Mapped[int | None] = mapped_column(Integer)
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


class VisitRecordOrm(Base):
    """방문 하나의 미용 기록(설계 6.1). 행이 있다는 것이 곧 '기록이 있다'이다."""

    __tablename__ = "visit_records"
    __table_args__ = (
        CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_visit_records_weight"),
        CheckConstraint(
            "payment_method IS NULL OR payment_method IN ('card', 'cash', 'transfer')",
            name="ck_visit_records_payment_method",
        ),
        CheckConstraint(
            "total_amount IS NULL OR total_amount BETWEEN 0 AND 100000000", name="ck_visit_records_total_amount"
        ),
        CheckConstraint("version >= 1", name="ck_visit_records_version"),
    )

    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    care_note: Mapped[str | None] = mapped_column(String(1000))       # 공개 — ⑤ 알림장
    internal_note: Mapped[str | None] = mapped_column(String(1000))   # 매장 안에서만
    payment_method: Mapped[str | None] = mapped_column(String(10))
    total_amount: Mapped[int | None] = mapped_column(Integer)         # 받은 돈. 항목 합과 다를 수 있다(할인)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    # tenancy 의 멤버 ID.
    created_by_member_id: Mapped[int] = mapped_column(BigInteger)
    updated_by_member_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VisitRecordItemOrm(Base):
    """실제로 한 메뉴와 금액. 예약 메뉴(visit_menus)와 다른 사실이다."""

    __tablename__ = "visit_record_items"
    __table_args__ = (
        CheckConstraint("amount BETWEEN 0 AND 100000000", name="ck_visit_record_items_amount"),
    )

    visit_id: Mapped[int] = mapped_column(
        ForeignKey("visit_records.visit_id", ondelete="CASCADE"), primary_key=True
    )
    menu_id: Mapped[int] = mapped_column(ForeignKey("service_menus.id"), primary_key=True)
    amount: Mapped[int] = mapped_column(Integer)


class VisitRecordMediaOrm(Base):
    """기록에 붙은 사진·영상. media_id 는 media 스포크의 ID 라 외래 키가 없다 — 정합성은 가져가기(claim)가 지킨다."""

    __tablename__ = "visit_record_media"
    __table_args__ = (
        CheckConstraint("kind IN ('photo', 'video')", name="ck_visit_record_media_kind"),
        CheckConstraint("phase IN ('before', 'after')", name="ck_visit_record_media_phase"),
        CheckConstraint("sort_order BETWEEN 0 AND 99", name="ck_visit_record_media_sort_order"),
        Index("uq_visit_record_media_order", "visit_id", "phase", "sort_order", unique=True),
    )

    visit_id: Mapped[int] = mapped_column(
        ForeignKey("visit_records.visit_id", ondelete="CASCADE"), primary_key=True
    )
    # 한 객체는 한 기록에만 붙는다.
    media_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True, autoincrement=False)
    kind: Mapped[str] = mapped_column(String(10))
    phase: Mapped[str] = mapped_column(String(10))
    sort_order: Mapped[int] = mapped_column(SmallInteger)
    hidden_from_report: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))   # ⑤ 알림장에서 뺀 사진


class VisitReportOrm(Base):
    """알림장 링크 하나(설계 4.1). 매장은 방문에서 읽는다. 토큰은 저장하지 않는다 — public_id 와 서버 키로 계산한다."""

    __tablename__ = "visit_reports"
    __table_args__ = (
        CheckConstraint("expires_at IS NULL OR expires_at > created_at", name="ck_visit_reports_expires"),
        CheckConstraint("octet_length(public_id) = 16", name="ck_visit_reports_public_id"),
        # 방문당 끊지 않은 줄은 하나. 색인에 현재 시각을 넣을 수 없어 기간이 지난 줄은 발급이 먼저 닫는다.
        Index("uq_visit_reports_live", "visit_id", unique=True, postgresql_where=text("revoked_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"))
    public_id: Mapped[bytes] = mapped_column(LargeBinary(16), unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))   # NULL 이면 무기한
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_member_id: Mapped[int] = mapped_column(BigInteger)   # tenancy 의 멤버 ID
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    show_review: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))   # 리뷰 줄을 넣는가(0024)
