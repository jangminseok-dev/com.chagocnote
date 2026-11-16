"""서류 요청과 동의서 서명의 표(⑪-A, 마이그레이션 0018)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, LargeBinary, SmallInteger, String,
    UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class CustomerFormOrm(Base):
    """보호자에게 보낸 서류 링크 하나. 토큰은 저장하지 않는다 — public_id 와 서버 키로 그때마다 계산한다."""

    __tablename__ = "customer_forms"
    __table_args__ = (
        CheckConstraint("kind IN ('consent', 'intake')", name="ck_customer_forms_kind"),
        CheckConstraint("octet_length(public_id) = 16", name="ck_customer_forms_public_id_length"),
        UniqueConstraint("public_id", name="uq_customer_forms_public_id"),
        Index("ix_customer_forms_shop_customer", "shop_id", "customer_id"),
        Index(
            "uq_customer_forms_live_intake_pet", "intake_pet_id", unique=True,
            postgresql_where=text("kind = 'intake' AND revoked_at IS NULL AND submitted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(10))
    public_id: Mapped[bytes] = mapped_column(LargeBinary)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_member_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # 문서를 조립하는 기준일(예약 날). 없으면 여는 날이다(0019).
    for_date: Mapped[date | None] = mapped_column(Date)
    # 이미 있는 아이의 정보를 다시 받는 문진표가 가리키는 아이(0021). 그런 요청은 아이마다 하나만 산다.
    intake_pet_id: Mapped[int | None] = mapped_column(ForeignKey("pets.id"))
    # 이 문진표 링크로 받은 답의 수(0022) — 답을 지워도 줄지 않는다(한 링크에 열 마리까지).
    intake_answered: Mapped[int] = mapped_column(SmallInteger, server_default="0")


class CustomerFormPetOrm(Base):
    """동의서 요청이 담는 아이."""

    __tablename__ = "customer_form_pets"
    __table_args__ = (Index("ix_customer_form_pets_pet_id", "pet_id"),)

    form_id: Mapped[int] = mapped_column(ForeignKey("customer_forms.id", ondelete="CASCADE"), primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), primary_key=True)


class ConsentSignatureOrm(Base):
    """서명 한 번. 그림·적은 이름은 개인정보다 — 로그에 남기지 않고, 익명화·삭제 때 지운다."""

    __tablename__ = "consent_signatures"
    __table_args__ = (
        CheckConstraint("channel IN ('link', 'in_shop', 'intake')", name="ck_consent_signatures_channel"),
        CheckConstraint("customer_id IS NOT NULL OR intake_answer_id IS NOT NULL", name="ck_consent_signatures_owner"),
        CheckConstraint("octet_length(signature_png) <= 65536", name="ck_consent_signatures_png_size"),
        CheckConstraint("(channel = 'link') = (form_id IS NOT NULL)", name="ck_consent_signatures_link_has_form"),
        UniqueConstraint("form_id", name="uq_consent_signatures_form_id"),
        Index("ix_consent_signatures_shop_customer", "shop_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))   # 맡아 둔 서명은 없다(⑪-C1b)
    form_id: Mapped[int | None] = mapped_column(ForeignKey("customer_forms.id"))
    # 문진표 끝에서 받아 맡아 둔 서명 — 그 답에 매달려 있다가 등록·반영이 떼어 내 아이에게 붙인다(0023).
    intake_answer_id: Mapped[int | None] = mapped_column(
        ForeignKey("intake_answers.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(10))
    signer_name: Mapped[str] = mapped_column(String(50))
    signature_png: Mapped[bytes] = mapped_column(LargeBinary)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    by_member_id: Mapped[int] = mapped_column(BigInteger)


class ConsentSignaturePetOrm(Base):
    """서명이 덮은 아이 하나와 그때 보인 이름(사본)."""

    __tablename__ = "consent_signature_pets"
    __table_args__ = (
        Index("ix_consent_signature_pets_signature_id", "signature_id"),
        Index("ix_consent_signature_pets_pet_id", "pet_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    signature_id: Mapped[int] = mapped_column(ForeignKey("consent_signatures.id", ondelete="CASCADE"))
    pet_id: Mapped[int | None] = mapped_column(ForeignKey("pets.id"))
    shown_pet_name: Mapped[str] = mapped_column(String(50))


class ConsentSignaturePartOrm(Base):
    """그 아이에 대해 읽은 토막과 그 글의 출처·판."""

    __tablename__ = "consent_signature_parts"
    __table_args__ = (
        CheckConstraint("part IN ('basic', 'senior', 'condition')", name="ck_consent_signature_parts_part"),
        CheckConstraint("text_source IN ('default', 'shop')", name="ck_consent_signature_parts_source"),
    )

    signature_pet_id: Mapped[int] = mapped_column(
        ForeignKey("consent_signature_pets.id", ondelete="CASCADE"), primary_key=True)
    part: Mapped[str] = mapped_column(String(10), primary_key=True)
    text_source: Mapped[str] = mapped_column(String(10))
    text_version: Mapped[int] = mapped_column(Integer)


class ConsentSignatureConditionOrm(Base):
    """그때 보인 지병 이름(사본) — 뒤에 지병이 늘었는지 견줄 때 쓴다."""

    __tablename__ = "consent_signature_conditions"

    signature_pet_id: Mapped[int] = mapped_column(
        ForeignKey("consent_signature_pets.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    label: Mapped[str] = mapped_column(String(50))
