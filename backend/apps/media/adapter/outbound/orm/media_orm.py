from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class MediaObjectOrm(Base):
    """사진·영상 객체 하나(설계 6.1). 상태가 원본이고 크기·준비 시각은 ready 일 때만 있다(CHECK)."""

    __tablename__ = "media_objects"
    __table_args__ = (
        CheckConstraint("kind IN ('photo', 'video')", name="ck_media_objects_kind"),
        CheckConstraint("status IN ('pending', 'ready')", name="ck_media_objects_status"),
        CheckConstraint(
            "(status = 'ready') = (ready_at IS NOT NULL) AND (status = 'ready') = (size_bytes IS NOT NULL)",
            name="ck_media_objects_ready_fields",
        ),
        CheckConstraint("attached_at IS NULL OR status = 'ready'", name="ck_media_objects_attached_ready"),
        CheckConstraint("(kind = 'photo') = (display_key IS NOT NULL)", name="ck_media_objects_display"),
        CheckConstraint("(kind = 'video') = (duration_seconds IS NOT NULL)", name="ck_media_objects_duration"),
        CheckConstraint("width > 0 AND height > 0", name="ck_media_objects_size"),
        Index("ix_media_objects_shop_status_created", "shop_id", "status", "created_at"),
        # 정리 스크립트의 "준비됐지만 어느 기록도 가져가지 않은 것"(설계 7.5 ②).
        Index("ix_media_objects_unattached", "ready_at",
              postgresql_where=text("status = 'ready' AND attached_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # tenancy 의 매장 ID. 스포크를 넘는 외래 키는 걸지 않는다.
    shop_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10))
    object_key: Mapped[str] = mapped_column(String(100), unique=True)
    display_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    thumb_key: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(20))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int] = mapped_column(SmallInteger)
    height: Mapped[int] = mapped_column(SmallInteger)
    duration_seconds: Mapped[int | None] = mapped_column(SmallInteger)
    # tenancy 의 멤버 ID.
    uploaded_by_member_id: Mapped[int] = mapped_column(BigInteger)
    attached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
