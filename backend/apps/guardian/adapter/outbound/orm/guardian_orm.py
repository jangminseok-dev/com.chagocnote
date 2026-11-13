from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, text
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
        # 고객 카드 하나에 살아 있는 연결은 하나.
        Index("uq_guardian_links_live", "shop_id", "customer_id", unique=True,
              postgresql_where=text("ended_at IS NULL")),
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
