from __future__ import annotations

from sqlalchemy import func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from media.adapter.outbound.mappers.media_mapper import to_media
from media.adapter.outbound.orm.media_orm import MediaObjectOrm
from media.app.ports.output.media_repository import MediaRepository
from media.domain.entities.media_object import PENDING, READY, MediaObject
from media.domain.errors import MediaNotFoundError
from media.domain.services.media_rules import object_keys
from media.domain.value_objects.new_media import NewMedia


class MediaPgRepository(MediaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, ctx: ShopContext, new: NewMedia) -> MediaObject:
        # 키가 ID 를 품으므로 ID 를 먼저 받는다.
        media_id = (await self._session.execute(text("SELECT nextval('media_objects_id_seq')"))).scalar_one()
        keys = object_keys(ctx.shop_id, media_id, new.kind)
        await self._session.execute(
            insert(MediaObjectOrm).values(
                id=media_id, shop_id=ctx.shop_id, kind=new.kind, status=PENDING,
                object_key=keys.original, display_key=keys.display, thumb_key=keys.thumb,
                content_type=new.content_type, width=new.width, height=new.height,
                duration_seconds=new.duration_seconds, uploaded_by_member_id=new.uploaded_by_member_id,
            )
        )
        return await self.get(ctx, media_id)

    async def get(self, ctx: ShopContext, media_id: int) -> MediaObject:
        row = (
            await self._session.execute(
                select(MediaObjectOrm)
                .where(MediaObjectOrm.id == media_id, MediaObjectOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise MediaNotFoundError("사진·영상을 찾을 수 없습니다.")
        return to_media(row)

    async def mark_ready(self, ctx: ShopContext, media_id: int, size_bytes: int) -> bool:
        result = await self._session.execute(
            update(MediaObjectOrm)
            .where(MediaObjectOrm.id == media_id, MediaObjectOrm.shop_id == ctx.shop_id,
                   MediaObjectOrm.status == PENDING)
            .values(status=READY, size_bytes=size_bytes, ready_at=func.now())
        )
        return result.rowcount == 1

    async def attach_all(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, str] | None:
        wanted = set(media_ids)
        savepoint = await self._session.begin_nested()
        # 조건부 UPDATE — 같은 미디어를 동시에 가져가는 두 요청 가운데 늦은 쪽은 앞선 쪽이 커밋할 때까지 행에서
        # 기다렸다가 조건(attached_at IS NULL)을 다시 보고 0행이 된다.
        rows = (
            await self._session.execute(
                update(MediaObjectOrm)
                .where(MediaObjectOrm.id.in_(wanted), MediaObjectOrm.shop_id == ctx.shop_id,
                       MediaObjectOrm.status == READY, MediaObjectOrm.attached_at.is_(None))
                .values(attached_at=func.now())
                .returning(MediaObjectOrm.id, MediaObjectOrm.kind)
            )
        ).all()
        if len(rows) != len(wanted):
            await savepoint.rollback()
            return None
        await savepoint.commit()
        return {media_id: kind for media_id, kind in rows}

    async def detach(self, ctx: ShopContext, media_ids: list[int]) -> None:
        await self._session.execute(
            update(MediaObjectOrm)
            .where(MediaObjectOrm.id.in_(media_ids), MediaObjectOrm.shop_id == ctx.shop_id)
            .values(attached_at=None)
        )

    async def list(self, ctx: ShopContext, media_ids: list[int]) -> list[MediaObject]:
        rows = (
            await self._session.execute(
                select(MediaObjectOrm)
                .where(MediaObjectOrm.id.in_(media_ids), MediaObjectOrm.shop_id == ctx.shop_id)
                .order_by(MediaObjectOrm.id)
                .execution_options(populate_existing=True)
            )
        ).scalars()
        return [to_media(row) for row in rows]
