from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from guardian.domain.entities.guardian_link import ENDED_BY, VERIFIED_BY


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class GuardianLinkOrm(Base):
    """보호자 계정과 고객 카드의 연결(⑦ 설계 4.2). 전화번호·이름을 저장하지 않는다."""

    __tablename__ = "guardian_links"
    __table_args__ = (
        CheckConstraint(_in("verified_by", VERIFIED_BY), name="ck_guardian_links_verified_by"),
        CheckConstraint("ended_by IS NULL OR " + _in("ended_by", ENDED_BY), name="ck_guardian_links_ended_by"),
        CheckConstraint("(ended_at IS NULL) = (ended_by IS NULL)", name="ck_guardian_links_ended"),
        CheckConstraint("(parent_link_id IS NULL) = (verified_by <> 'family_invite')", name="ck_guardian_links_family"),
        # 고객 카드 하나에 살아 있는 **기본** 연결은 하나. 가족 연결은 기본 연결 아래에 붙는다(⑫).
        Index("uq_guardian_links_live", "shop_id", "customer_id", unique=True,
              postgresql_where=text("ended_at IS NULL AND parent_link_id IS NULL")),
        # 같은 계정이 같은 기본 연결의 가족으로 두 번 붙지 않는다.
        Index("uq_guardian_links_family", "parent_link_id", "user_id", unique=True,
              postgresql_where=text("ended_at IS NULL AND parent_link_id IS NOT NULL")),
        Index("ix_guardian_links_user", "user_id", postgresql_where=text("ended_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    customer_id: Mapped[int] = mapped_column(BigInteger)
    verified_by: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_by: Mapped[str | None] = mapped_column(String(20))
    parent_link_id: Mapped[int | None] = mapped_column(ForeignKey("guardian_links.id"))   # 가족 연결이면 기본 연결
    seen_by_primary_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuardianFamilyInviteOrm(Base):
    """가족 초대(⑫). 코드 원문은 저장하지 않는다. 이 표의 줄을 '가족 초대 행'이라 부른다(매장 초대와 가른다)."""

    __tablename__ = "guardian_family_invites"
    __table_args__ = (
        UniqueConstraint("code_hash", name="uq_guardian_family_invites_code_hash"),
        Index("ix_guardian_family_invites_link_id", "link_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("guardian_links.id"))
    code_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuardianShopSettingsOrm(Base):
    """매장이 정하는 가족 수(⑫ 8절). 행이 없으면 기본 3."""

    __tablename__ = "guardian_shop_settings"
    __table_args__ = (CheckConstraint("family_max BETWEEN 0 AND 10", name="ck_guardian_shop_settings_family_max"),)

    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    family_max: Mapped[int] = mapped_column(SmallInteger, server_default="3")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
