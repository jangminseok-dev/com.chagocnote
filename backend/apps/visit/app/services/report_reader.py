"""알림장을 보여 줄 모양으로 조립한다 — 공개 조회와 매장의 미리보기가 같은 함수를 쓴다.

매장이 끈 항목과 뺀 사진은 여기서 뺀다. 반려동물 이름은 허브 포트로 읽고 보호자는 읽지 않는다(설계 6.3).
"""
from __future__ import annotations

from dataclasses import replace

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.report_view_dto import (
    ReportCoverView,
    ReportLinkView,
    ReportMediaView,
    ReportMenuView,
    ReportShopView,
    ReportView,
)
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.entities.visit import Visit
from visit.domain.entities.visit_record import VisitRecord
from visit.domain.entities.visit_report import VisitReport
from visit.domain.services.report_rules import hide, report_cover_media_id, review_of, visible_media
from core.link_token import make_token
from visit.domain.services.visit_schedule import local_date
from visit.domain.value_objects.report_settings import ReportSettings


async def describe_report(
    ctx: ShopContext, visit: Visit, record: VisitRecord, settings: ReportSettings, shop: ShopProfile,
    menus: MenuRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort, *, include_hidden: bool,
    show_review: bool = True,
) -> ReportView:
    hidden = {m.media_id for m in record.media if m.hidden}
    # 미리보기는 뺀 것도 같은 순서로 보여 준다 — 표시를 모두 지운 기록에 보이는 순서 규칙을 그대로 쓴다.
    shown = visible_media(replace(record, media=hide(record, ())) if include_hidden else record)
    urls = await library.read_urls(ctx, [m.media_id for m in shown])
    cover = urls.get(report_cover_media_id(record))
    # 리뷰 남기기 줄(⑫) — 미리보기는 그 알림장이 뺐어도 주소를 보인다(스위치 곁에 그린다).
    review_url, review_text = review_of(settings, show_review or include_hidden)
    return ReportView(
        pet_name=await _pet_name(ctx, visit, directory),
        visit_date=local_date(visit.starts_at, ctx.timezone),
        care_note=record.care_note if record.care_note and record.care_note.strip() else None,
        media=tuple(
            ReportMediaView(
                media_id=m.media_id, kind=m.kind, phase=m.phase, hidden=m.media_id in hidden,
                width=urls[m.media_id].width, height=urls[m.media_id].height,
                duration_seconds=urls[m.media_id].duration_seconds,
                display_url=urls[m.media_id].display_url or urls[m.media_id].original_url,
                thumb_url=urls[m.media_id].thumb_url, download_url=urls[m.media_id].download_url,
            )
            for m in shown if m.media_id in urls
        ),
        cover=ReportCoverView(url=cover.display_url or cover.thumb_url, width=cover.width, height=cover.height)
        if cover else None,
        menus=await _menus(ctx, record, settings, menus) if settings.show_menus else None,
        total_amount=record.total_amount if settings.show_amount else None,
        weight_kg=record.weight_kg if settings.show_weight else None,
        shop=ReportShopView(name=shop.name, phone=shop.phone, address=shop.address)
        if settings.show_shop_info else None,
        settings=settings,
        review_url=review_url,
        review_text=review_text,
    )


async def _pet_name(ctx: ShopContext, visit: Visit, directory: CustomerDirectoryPort) -> str | None:
    """익명화한 고객의 아이는 이름이 없고 지워진 아이는 요약에 없다. 무지개다리를 건넌 아이는 이름이 남아 있다."""
    if visit.pet_id is None:
        return None
    pet = (await directory.briefs(ctx, [], [visit.pet_id])).pets.get(visit.pet_id)
    return pet.name if pet else None


async def _menus(
    ctx: ShopContext, record: VisitRecord, settings: ReportSettings, menus: MenuRepository
) -> tuple[ReportMenuView, ...]:
    """실제로 한 메뉴(기록의 항목). 이름은 메뉴표(보관한 것도)에서 읽는다."""
    if not record.items:
        return ()
    names = {m.id: m.name for m in await menus.list_by_ids(ctx, [i.menu_id for i in record.items])}
    return tuple(
        ReportMenuView(name=names[i.menu_id], amount=i.amount if settings.show_amount else None)
        for i in record.items
    )


def describe_link(report: VisitReport | None, key: bytes, base_url: str) -> ReportLinkView:
    """report 는 살아 있는 링크(없으면 None). 주소는 저장하지 않고 public_id 와 키로 그때마다 만든다."""
    if report is None:
        return ReportLinkView(status="none", url=None, expires_at=None, first_viewed_at=None, created_at=None)
    return ReportLinkView(
        status="live", url=f"{base_url}/r/{make_token(report.public_id, key)}", expires_at=report.expires_at,
        first_viewed_at=report.first_viewed_at, created_at=report.created_at, show_review=report.show_review,
    )
