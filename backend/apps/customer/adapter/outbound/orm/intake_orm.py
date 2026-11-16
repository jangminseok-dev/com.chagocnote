"""문진표의 표(⑪-C, 마이그레이션 0021). 받은 답은 개인정보다 — 로그에 남기지 않고 등록·지우기·기한에서 지운다."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Numeric, SmallInteger, String, false,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ShopIntakeQuestionOrm(Base):
    """매장이 문진표에 더한 질문. 지워도 행은 남는다 — 받은 답이 가리킨다."""

    __tablename__ = "shop_intake_questions"
    __table_args__ = (Index("ix_shop_intake_questions_shop_id", "shop_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    position: Mapped[int] = mapped_column(SmallInteger)
    label: Mapped[str] = mapped_column(String(100))
    required: Mapped[bool] = mapped_column(Boolean)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntakeAnswerOrm(Base):
    """받은 문진표 하나(아이 한 마리). 끈 칸·모르겠어요는 NULL 이다 — 지어내지 않는다."""

    __tablename__ = "intake_answers"
    __table_args__ = (
        Index("ix_intake_answers_shop_id", "shop_id"),
        Index("ix_intake_answers_form_id", "form_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    form_id: Mapped[int] = mapped_column(ForeignKey("customer_forms.id"))
    matched_customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    guardian_name: Mapped[str | None] = mapped_column(String(50))
    guardian_phone: Mapped[str | None] = mapped_column(String(20))
    pet_name: Mapped[str | None] = mapped_column(String(50))
    species: Mapped[str | None] = mapped_column(String(10))
    breed: Mapped[str | None] = mapped_column(String(50))
    sex: Mapped[str | None] = mapped_column(String(10))
    neutered: Mapped[bool | None] = mapped_column(Boolean)
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    birth_unknown: Mapped[bool] = mapped_column(Boolean, server_default=false())
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    no_known_conditions: Mapped[bool | None] = mapped_column(Boolean)
    dislikes: Mapped[str | None] = mapped_column(String(200))
    style: Mapped[str | None] = mapped_column(String(200))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IntakeAnswerConditionOrm(Base):
    __tablename__ = "intake_answer_conditions"

    answer_id: Mapped[int] = mapped_column(ForeignKey("intake_answers.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    type_code: Mapped[str] = mapped_column(String(30))
    custom_label: Mapped[str | None] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(100))


class IntakeAnswerExtraOrm(Base):
    """매장이 더한 질문의 답."""

    __tablename__ = "intake_answer_extras"

    answer_id: Mapped[int] = mapped_column(ForeignKey("intake_answers.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("shop_intake_questions.id"), primary_key=True)
    body: Mapped[str] = mapped_column(String(200))
