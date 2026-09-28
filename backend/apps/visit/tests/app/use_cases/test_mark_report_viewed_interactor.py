from dataclasses import replace

import pytest

from visit.app.dtos.mark_report_viewed_dto import MarkReportViewedCommand
from visit.app.use_cases.mark_report_viewed_interactor import MarkReportViewedInteractor
from visit.domain.errors import ReportClosedError, ReportNotFoundError, TooManyReportRequestsError
from visit.tests.helpers.builders import kst
from visit.tests.helpers.public_world import CLIENT, KEY, NOW, SHOP, PublicWorld


async def _mark(world, token, now=NOW):
    interactor = MarkReportViewedInteractor(
        reports=world.reports, shops=world.shops, limiter=world.limiter, now=lambda: now, link_key=KEY)
    await interactor.mark_report_viewed(MarkReportViewedCommand(token=token, client=CLIENT))


def _viewed_at(world):
    return [r.first_viewed_at for r in world.reports.rows]


async def test_처음_연_시각을_남기고_다시_열어도_그대로다():
    """R10"""
    world = PublicWorld()
    token = await world.sent()
    await _mark(world, token)
    await _mark(world, token, now=kst(9, 25, 9))
    assert _viewed_at(world) == [NOW]


async def test_끊은_링크와_기간이_지난_링크에는_남기지_않는다():
    """R11"""
    world = PublicWorld()
    token = await world.sent(expires_at=kst(9, 24, 12))
    with pytest.raises(ReportClosedError):
        await _mark(world, token, now=kst(9, 24, 12))
    world.revoke()
    with pytest.raises(ReportClosedError):
        await _mark(world, token)
    assert (_viewed_at(world), world.reports.journal) == ([None], [("create_report", 1)])


@pytest.mark.parametrize("shop", [replace(SHOP, open=False), None], ids=["정지·폐업", "없는 매장"])
async def test_문을_닫은_매장의_알림장에는_남기지_않는다(shop):
    """R21"""
    world = PublicWorld()
    token = await world.sent()
    world.shops.shops = {1: shop} if shop else {}
    with pytest.raises(ReportClosedError):
        await _mark(world, token)
    assert _viewed_at(world) == [None]


async def test_우리가_만들지_않은_토큰은_저장소를_부르지_않고_404_다():
    world = PublicWorld()
    await world.sent()
    for token in (None, "a" * 43):
        with pytest.raises(ReportNotFoundError):
            await _mark(world, token)
    assert (world.reports.finds, _viewed_at(world), world.limiter.misses) == ([], [None], [CLIENT, CLIENT])


async def test_횟수_제한에_걸리면_남기지_않는다():
    world = PublicWorld()
    token = await world.sent()
    world.limiter.allowed = False
    with pytest.raises(TooManyReportRequestsError):
        await _mark(world, token)
    assert _viewed_at(world) == [None]
