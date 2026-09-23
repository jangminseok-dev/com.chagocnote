from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class CustomerOrm(Base):
    __tablename__ = "customers"
    __table_args__ = (
        # 익명화한 고객의 행은 남는다. 번호가 유일해야 하는 것은 살아 있는 고객뿐이다.
        Index(
            "uq_customers_shop_phone_active", "shop_id", "phone",
            unique=True, postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "deleted_at IS NOT NULL OR (name IS NOT NULL AND phone IS NOT NULL)",
            name="ck_customers_alive_has_name_phone",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # tenancy 의 매장 ID. 스포크를 넘는 외래 키는 걸지 않는다.
    shop_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(11))
    phone_alt: Mapped[str | None] = mapped_column(String(11))
    marketing_consent: Mapped[bool] = mapped_column(Boolean)
    marketing_consent_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    memo: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PetOrm(Base):
    __tablename__ = "pets"
    __table_args__ = (
        CheckConstraint("species IN ('dog', 'cat')", name="ck_pets_species"),
        CheckConstraint("sex IN ('female', 'male')", name="ck_pets_sex"),
        CheckConstraint("weight_kg > 0", name="ck_pets_weight_positive"),
        CheckConstraint("birth_date IS NULL OR birth_year IS NULL", name="ck_pets_one_birth_field"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 매장은 고객을 거쳐 안다. 여기에 shop_id 를 두지 않는다(이행 종속).
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(50))
    species: Mapped[str] = mapped_column(String(10))
    breed: Mapped[str] = mapped_column(String(50))
    sex: Mapped[str] = mapped_column(String(10))
    neutered: Mapped[bool] = mapped_column(Boolean)
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    no_known_conditions: Mapped[bool] = mapped_column(Boolean)
    memo: Mapped[str | None] = mapped_column(String(500))
    passed_away_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PetConditionTypeOrm(Base):
    """정해진 질병 종류. 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다."""

    __tablename__ = "pet_condition_types"

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    label: Mapped[str] = mapped_column(String(30))
    sort_order: Mapped[int] = mapped_column(SmallInteger)


class PetConditionOrm(Base):
    __tablename__ = "pet_conditions"
    __table_args__ = (
        # 같은 정해진 질병은 한 번만. 기타는 여러 개 넣을 수 있다.
        Index(
            "uq_pet_conditions_pet_type", "pet_id", "type_code",
            unique=True, postgresql_where=text("type_code <> 'other'"),
        ),
        CheckConstraint(
            "(type_code = 'other') = (custom_label IS NOT NULL)", name="ck_pet_conditions_other_label"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    type_code: Mapped[str] = mapped_column(ForeignKey("pet_condition_types.code"))
    custom_label: Mapped[str | None] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(100))


class CustomerSearchEntryOrm(Base):
    """검색용 역정규화 표(설계 6.4). 원본은 customers·pets 이고 언제든 다시 만들 수 있다."""

    __tablename__ = "customer_search_entries"
    __table_args__ = (
        Index(
            "ix_customer_search_entries_terms_trgm", "terms",
            postgresql_using="gin", postgresql_ops={"terms": "gin_trgm_ops"},
        ),
        Index("ix_customer_search_entries_shop_activity", "shop_id", "last_activity_at"),
        Index("ix_customer_search_entries_shop_sort_name", "shop_id", "sort_name"),
        Index("ix_customer_search_entries_shop_last_visit", "shop_id", "last_visit_at"),
    )

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    terms: Mapped[str] = mapped_column(Text)
    phone_last4: Mapped[str] = mapped_column(String(4))
    sort_name: Mapped[str] = mapped_column(String(50))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # 마지막 완료 방문의 시작 시각(최근 방문순). 원본은 visits 이고 visit 스포크가 허브 포트로 알려 준다.
    last_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
