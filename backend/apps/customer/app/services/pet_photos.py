"""반려동물 프로필 사진 — 가장 최근 완료 기록의 대표 사진(visit)을 썸네일 URL(media)로 바꾼다(설계 8절).

사진을 customer 에 복사해 두지 않는다. 목록·상세가 읽을 때마다 허브 포트 둘로 한 번씩 묻는다(N+1 없음).
"""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


async def pet_photos(
    ctx: ShopContext, pet_ids: list[int], ledger: VisitLedgerPort, library: MediaLibraryPort
) -> dict[int, str]:
    """{반려동물 ID: 썸네일 URL}. 사진이 없는 아이는 빠진다."""
    if not pet_ids:
        return {}
    covers = await ledger.latest_covers(ctx, pet_ids)
    urls = await library.read_urls(ctx, sorted(set(covers.values())))
    return {pet_id: urls[media_id].thumb_url for pet_id, media_id in covers.items() if media_id in urls}
