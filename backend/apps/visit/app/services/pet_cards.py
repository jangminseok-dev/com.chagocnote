"""매출 화면에 보일 아이 — 이름과 프로필 사진(사진이 붙은 가장 최근 완료 방문의 대표).

이름을 보일 수 없는 아이(익명화한 고객의 아이, 지운 아이)는 여기서 빠진다 — 합계에는 남고 얼굴에서만 뺀다(설계 ⑧ S3).
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from hub.app.dtos.family_brief import PetBrief
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.domain.services.visit_record_rules import cover_media_id


@dataclass(frozen=True)
class PetCard:
    pet_id: int
    name: str
    photo_url: str | None


async def showable_pets(
    ctx: ShopContext, pet_ids: Iterable[int], directory: CustomerDirectoryPort
) -> dict[int, PetBrief]:
    """보일 수 있는 아이만 — 이 매장에 있고 이름이 있는 아이. 한 번에 묻는다."""
    wanted = sorted(set(pet_ids))
    if not wanted:
        return {}
    briefs = await directory.briefs(ctx, [], wanted)
    return {pet_id: brief for pet_id, brief in briefs.pets.items() if brief.name is not None}


async def pet_cards(
    ctx: ShopContext, pets: dict[int, PetBrief], pet_ids: Iterable[int],
    records: VisitRecordRepository, library: MediaLibraryPort,
) -> dict[int, PetCard]:
    """pet_ids 가운데 보일 수 있는 아이(pets 에 있는)의 카드. 사진이 없으면 photo_url 이 None 이다.
    질의 수는 아이 수와 상관없다."""
    wanted = sorted({pet_id for pet_id in pet_ids if pet_id in pets})
    if not wanted:
        return {}
    latest = await records.latest_with_media(ctx, wanted)
    found = await records.list_many(ctx, sorted(set(latest.values()))) if latest else {}
    covers = {
        pet_id: cover_media_id(found[visit_id].media) for pet_id, visit_id in latest.items() if visit_id in found
    }
    urls = await library.read_urls(ctx, sorted({m for m in covers.values() if m is not None})) if covers else {}
    return {
        pet_id: PetCard(
            pet_id=pet_id, name=pets[pet_id].name,
            photo_url=urls[covers[pet_id]].thumb_url if covers.get(pet_id) in urls else None,
        )
        for pet_id in wanted
    }

