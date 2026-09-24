"""기록을 보여 줄 모양으로 조립한다 — 메뉴 이름은 메뉴표(보관한 것도)에서, 사진 URL 은 허브 포트로.

기록 쓰기·덧붙이기가 쓰기를 마친 뒤, 방문 상세가 읽을 때 같은 모양으로 돌려준다.
"""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.record_view_dto import RecordItemView, RecordMediaView, RecordView
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.entities.visit_record import VisitRecord


async def describe_record(
    ctx: ShopContext, record: VisitRecord, menus: MenuRepository, library: MediaLibraryPort
) -> RecordView:
    names = {m.id: m.name for m in await menus.list_by_ids(ctx, [i.menu_id for i in record.items])} \
        if record.items else {}
    urls = await library.read_urls(ctx, [m.media_id for m in record.media])
    return RecordView(
        visit_id=record.visit_id, weight_kg=record.weight_kg, care_note=record.care_note,
        internal_note=record.internal_note, payment_method=record.payment_method,
        total_amount=record.total_amount,
        items=[RecordItemView(menu_id=i.menu_id, name=names[i.menu_id], amount=i.amount) for i in record.items],
        media=[
            RecordMediaView(
                media_id=m.media_id, kind=m.kind, phase=m.phase, sort_order=m.sort_order,
                original_url=urls[m.media_id].original_url, display_url=urls[m.media_id].display_url,
                thumb_url=urls[m.media_id].thumb_url, width=urls[m.media_id].width,
                height=urls[m.media_id].height, duration_seconds=urls[m.media_id].duration_seconds,
            )
            for m in record.media if m.media_id in urls
        ],
        version=record.version,
    )
