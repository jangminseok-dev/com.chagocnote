"""알림장 토큰을 매장·고객으로 푼다(허브 ReportLinkPort) — 보호자 연결이 쓴다. 열림의 뜻은 공개 조회와 같다."""
from dataclasses import replace

import pytest

from hub.app.dtos.guardian import ReportLinkTarget
from visit.app.use_cases.resolve_report_link_interactor import ResolveReportLinkInteractor
from visit.domain.services.report_token import make_token
from visit.tests.helpers.builders import kst
from visit.tests.helpers.public_world import KEY, NOW, SHOP, PublicWorld


async def _resolve(world, token, now=NOW):
    interactor = ResolveReportLinkInteractor(
        reports=world.reports, records=world.records, shops=world.shops, now=lambda: now, link_key=KEY)
    return await interactor.resolve(token)


async def test_열린_알림장의_토큰은_매장과_고객을_준다():
    world = PublicWorld()
    assert await _resolve(world, await world.sent()) == ReportLinkTarget(shop_id=1, customer_id=1, live=True)
    # 잇기는 로그인한 계정으로 센다 — 접속 주소 제한기를 쓰지 않는다.
    assert (world.limiter.hits, world.limiter.misses) == ([], [])


@pytest.mark.parametrize("token", [None, "", "a" * 43, make_token(bytes(range(16)), bytes(32))],
                         ids=["없음", "빈 값", "서명 없는 43글자", "다른 키로 서명"])
async def test_우리가_만들지_않은_토큰은_저장소를_부르지_않고_None_이다(token):
    world = PublicWorld()
    await world.sent()
    assert await _resolve(world, token) is None
    assert world.reports.finds == []


async def test_서명은_맞지만_그런_링크가_없으면_None_이다():
    assert await _resolve(PublicWorld(), make_token(bytes(16), KEY)) is None


async def test_끊은_링크는_닫힌_것이다():
    world = PublicWorld()
    token = await world.sent()
    world.revoke()
    assert await _resolve(world, token) == ReportLinkTarget(shop_id=1, customer_id=1, live=False)


async def test_기간이_지난_링크는_닫힌_것이다():
    world = PublicWorld()
    token = await world.sent(expires_at=kst(9, 24, 9))
    assert (await _resolve(world, token)).live is False
    forever = PublicWorld()
    assert (await _resolve(forever, await forever.sent(expires_at=None))).live is True


@pytest.mark.parametrize("shop", [None, replace(SHOP, open=False)], ids=["없는 매장", "정지·폐업"])
async def test_매장이_없거나_닫혔으면_닫힌_것이다(shop):
    world = PublicWorld()
    token = await world.sent()
    if shop is None:
        world.shops.shops.clear()
    else:
        world.shops.shops[1] = shop
    assert (await _resolve(world, token)).live is False


async def test_기록이_없는_방문의_링크는_닫힌_것이다():
    world = PublicWorld()
    token = await world.sent()
    world.records.rows.clear()
    assert (await _resolve(world, token)).live is False
