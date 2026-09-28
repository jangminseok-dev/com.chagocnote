from dataclasses import replace

import pytest

from visit.app.dtos.read_public_report_dto import ReadPublicReportQuery
from visit.app.dtos.report_view_dto import ReportShopView
from visit.app.use_cases.read_public_report_interactor import ReadPublicReportInteractor
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.domain.services.report_token import make_token
from visit.tests.helpers.public_world import CLIENT, KEY, NOW, SHOP, PublicWorld


async def _read(world, token, client=CLIENT):
    interactor = ReadPublicReportInteractor(
        reports=world.reports, records=world.records, settings=world.settings, menus=world.menus,
        directory=world.directory, library=world.library, shops=world.shops, limiter=world.limiter,
        now=lambda: NOW, link_key=KEY,
    )
    return await interactor.read_public_report(ReadPublicReportQuery(token=token, client=client))


async def test_토큰으로_알림장을_읽는다_뺀_사진은_없다():
    world = PublicWorld()
    found = await _read(world, await world.sent())
    assert (found.report.pet_name, found.report.care_note) == ("아이101", "눈물 자국")
    assert [(m.media_id, m.hidden) for m in found.report.media] == [(51, False)]
    assert found.report.shop == ReportShopView(name="Hiss Haus", phone="02-123-4567", address=None)
    assert found.expires_at.isoformat() == "2026-10-23T15:00:00+09:00"
    assert (world.limiter.hits, world.limiter.misses) == ([CLIENT], [])


async def test_날짜와_끝나는_시각은_매장_시간대로_센다():
    world = PublicWorld()
    world.shops.shops[1] = replace(SHOP, timezone="America/New_York")
    found = await _read(world, await world.sent())
    assert found.report.visit_date.isoformat() == "2026-09-23"     # 한국 14시는 뉴욕 같은 날 새벽 1시
    assert found.expires_at.isoformat() == "2026-10-23T02:00:00-04:00"


async def test_기간이_없는_링크는_끝나는_시각이_없다():
    world = PublicWorld()
    assert (await _read(world, await world.sent(expires_at=None))).expires_at is None


@pytest.mark.parametrize("token", [None, "", "a" * 43, make_token(bytes(range(16)), bytes(32))],
                         ids=["없음", "빈 값", "서명 없는 43글자", "다른 키로 서명"])
async def test_우리가_만들지_않은_토큰은_저장소를_부르지_않고_404_다(token):
    """R13 — 서명을 확인한 public_id 만 저장소에 넘긴다."""
    world = PublicWorld()
    await world.sent()
    with pytest.raises(ReportNotFoundError):
        await _read(world, token)
    assert world.reports.finds == []
    assert world.limiter.misses == [CLIENT]


async def test_서명은_맞지만_그런_링크가_없으면_404_다():
    world = PublicWorld()
    with pytest.raises(ReportNotFoundError):
        await _read(world, make_token(bytes(16), KEY))
    assert world.reports.finds == [bytes(16)]
    assert world.limiter.misses == [CLIENT]


async def test_끊은_링크는_410_이다():
    """R3"""
    world = PublicWorld()
    token = await world.sent()
    world.revoke()
    with pytest.raises(ReportClosedError):
        await _read(world, token)
    assert world.limiter.misses == []     # 닫힌 링크는 실패로 세지 않는다


async def test_기간이_지난_링크는_410_이다():
    """R3 — 끝나는 바로 그 시각에도 닫혀 있다."""
    world = PublicWorld()
    token = await world.sent(expires_at=NOW)
    with pytest.raises(ReportClosedError):
        await _read(world, token)


@pytest.mark.parametrize("shop", [replace(SHOP, open=False), None], ids=["정지·폐업", "없는 매장"])
async def test_문을_닫았거나_없는_매장의_알림장은_410_이다(shop):
    """R21"""
    world = PublicWorld()
    token = await world.sent()
    world.shops.shops = {1: shop} if shop else {}
    with pytest.raises(ReportClosedError):
        await _read(world, token)


async def test_기록이_없으면_410_이다():
    world = PublicWorld()
    token = await world.sent()
    world.records.rows.clear()
    with pytest.raises(ReportClosedError):
        await _read(world, token)


async def test_횟수_제한에_걸리면_토큰을_보지도_않고_429_다():
    """R1"""
    world = PublicWorld()
    token = await world.sent()
    world.limiter.allowed = False
    with pytest.raises(TooManyReportRequestsError):
        await _read(world, token)
    assert (world.reports.finds, world.limiter.misses) == ([], [])


async def test_알림장은_권한이_빈_컨텍스트로_읽는다():
    world = PublicWorld()
    seen = []

    async def read_urls(ctx, media_ids):
        seen.append(ctx)
        return {}

    world.library.read_urls = read_urls
    await _read(world, await world.sent())
    assert [(c.shop_id, c.member_id, c.role, c.permissions) for c in seen] == [(1, 0, "public", frozenset())]
