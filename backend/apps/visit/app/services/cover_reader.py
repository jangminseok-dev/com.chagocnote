"""대표 사진의 썸네일 URL — 방문마다 대표를 도메인 규칙(`cover_media_id`)으로 고르고 URL 은 허브 포트로 한 번에 받는다."""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.domain.entities.visit_record import VisitRecord
from visit.domain.services.visit_record_rules import cover_media_id


async def cover_urls(
    ctx: ShopContext, records: dict[int, VisitRecord], library: MediaLibraryPort
) -> dict[int, str]:
    """{방문 ID: 대표 사진의 썸네일 URL}. 사진·영상이 없는 방문은 빠진다."""
    covers = {visit_id: cover_media_id(record.media) for visit_id, record in records.items()}
    urls = await library.read_urls(ctx, sorted({m for m in covers.values() if m is not None}))
    return {visit_id: urls[m].thumb_url for visit_id, m in covers.items() if m in urls}
