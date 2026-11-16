"""서류 설정과 매장이 고친 동의서 글의 표(⑪-B, 마이그레이션 0020)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Integer, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ShopFormSettingsOrm(Base):
    """매장이 바꾼 서류의 기준값. 행이 없으면 기본값이고, 글 칸이 비어 있으면 기본 글이다."""

    __tablename__ = "shop_form_settings"
    __table_args__ = (
        CheckConstraint("link_days BETWEEN 1 AND 30", name="ck_shop_form_settings_link_days"),
        CheckConstraint("senior_age BETWEEN 5 AND 20", name="ck_shop_form_settings_senior_age"),
        CheckConstraint("consent_days BETWEEN 30 AND 1095", name="ck_shop_form_settings_consent_days"),
        CheckConstraint("intake_keep_days BETWEEN 7 AND 90", name="ck_shop_form_settings_intake_keep_days"),
    )

    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    link_days: Mapped[int] = mapped_column(SmallInteger)
    senior_age: Mapped[int] = mapped_column(SmallInteger)
    consent_days: Mapped[int] = mapped_column(SmallInteger)
    reservation_text: Mapped[str | None] = mapped_column(String(500))
    consent_text: Mapped[str | None] = mapped_column(String(500))
    # 문진표(0021) — 확인하지 않은 답을 지우는 날 수, 매장이 끈 칸.
    intake_keep_days: Mapped[int] = mapped_column(SmallInteger, server_default="30")
    intake_hidden: Mapped[list[str]] = mapped_column(ARRAY(String(20)), server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShopConsentTextOrm(Base):
    """매장이 고친 동의서 토막의 글 한 판. 쌓기만 한다. body 가 없으면 기본 글로 되돌린 판이다."""

    __tablename__ = "shop_consent_texts"
    __table_args__ = (
        CheckConstraint("part IN ('basic', 'senior', 'condition')", name="ck_shop_consent_texts_part"),
        UniqueConstraint("shop_id", "part", "version", name="uq_shop_consent_texts_shop_part_version"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    part: Mapped[str] = mapped_column(String(10))
    version: Mapped[int] = mapped_column(Integer)
    body: Mapped[str | None] = mapped_column(String(2000))
    created_by_member_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
