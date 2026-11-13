"""잇기 — 받은 알림장 링크로 고객 카드와 계정을 잇는다(스텁). 고객 카드 하나에 계정 하나."""
import pytest

from guardian.app.dtos.claim_guardian_link_dto import ClaimGuardianLinkCommand
from guardian.app.use_cases.claim_guardian_link_interactor import ClaimGuardianLinkInteractor
from guardian.domain.errors import (
    GuardianAccountInactiveError,
    GuardianAlreadyLinkedError,
    ReportLinkClosedError,
    ReportLinkNotFoundError,
    TooManyGuardianRequestsError,
)
from guardian.tests.helpers.builders import kst
from guardian.tests.helpers.fakes import FakeActiveUsers, FakeClaimLimiter, FakeLinks, FakeReportLinks
from hub.app.dtos.guardian import ReportLinkTarget

NOW = kst(11, 13, 10)
TOKEN = "열린-토큰"


class _World:
    def __init__(self, limit: int = 10) -> None:
        self.journal: list = []
        self.links = FakeLinks(self.journal)
        self.reports = FakeReportLinks(self.journal)
        self.users = FakeActiveUsers(self.journal)
        self.limiter = FakeClaimLimiter(limit, self.journal)
        self.reports.targets[TOKEN] = ReportLinkTarget(shop_id=3, customer_id=7, live=True)
        self.reports.targets["닫힌-토큰"] = ReportLinkTarget(shop_id=3, customer_id=8, live=False)
        self.interactor = ClaimGuardianLinkInteractor(
            links=self.links, reports=self.reports, users=self.users, limiter=self.limiter, now=lambda: NOW)

    async def claim(self, user_id=5, token=TOKEN):
        return await self.interactor.claim(ClaimGuardianLinkCommand(user_id=user_id, token=token))


async def test_열린_링크로_이으면_연결이_생긴다():
    world = _World()
    result = await world.claim()
    assert (result.link_id, result.created) == (1, True)
    row = world.links.rows[1]
    assert (row.user_id, row.shop_id, row.customer_id, row.verified_by, row.created_at) == (5, 3, 7, "report_link", NOW)


async def test_이미_내_연결이면_같은_ID_를_돌려주고_줄이_늘지_않는다():
    world = _World()
    first = await world.claim()
    again = await world.claim()
    assert (again.link_id, again.created) == (first.link_id, False)
    assert len(world.links.rows) == 1


async def test_남의_계정에_이어진_카드는_409_다():
    world = _World()
    await world.claim(user_id=5)
    with pytest.raises(GuardianAlreadyLinkedError):
        await world.claim(user_id=6)
    assert len(world.links.rows) == 1


async def test_닫힌_알림장으로는_잇지_못한다():
    world = _World()
    with pytest.raises(ReportLinkClosedError):
        await world.claim(token="닫힌-토큰")
    assert world.links.rows == {}


@pytest.mark.parametrize("token", [None, "없는-토큰"])
async def test_토큰이_없거나_우리_것이_아니면_404_다(token):
    world = _World()
    with pytest.raises(ReportLinkNotFoundError):
        await world.claim(token=token)


async def test_한도를_넘으면_429_이고_잠금도_토큰_확인도_하지_않는다():
    world = _World(limit=1)
    await world.claim()
    world.journal.clear()
    with pytest.raises(TooManyGuardianRequestsError):
        await world.claim()
    assert world.journal == [("count_claim", 5)]


async def test_끊은_뒤_다시_이으면_새_연결이고_옛_줄은_끝난_채_남는다():
    world = _World()
    first = await world.claim()
    await world.links.end(first.link_id, "guardian", NOW)
    again = await world.claim()
    assert (again.link_id, again.created) == (2, True)
    assert (world.links.rows[1].is_live, world.links.rows[1].ended_by, world.links.rows[2].is_live) == (
        False, "guardian", True)


async def test_유저_행을_먼저_잠그고_그_뒤에_토큰을_확인한다():
    world = _World()
    await world.claim()
    assert world.journal == [("count_claim", 5), ("lock_user", 5), ("resolve_token",), ("create_link", 5, 3, 7)]


async def test_탈퇴했거나_정지된_계정은_잇지_못한다():
    world = _World()
    world.users.inactive.add(5)
    with pytest.raises(GuardianAccountInactiveError):
        await world.claim()
    assert world.links.rows == {}


async def test_동시에_온_둘째는_저장소의_409_가_그대로_올라온다():
    world = _World()

    async def raced(shop_id, customer_id):
        return None   # 확인할 때는 없었다 — 그 사이 다른 계정이 먼저 이었다

    await world.links.create(6, 3, 7, "report_link", NOW)
    world.links.find_live_for_customer = raced
    with pytest.raises(GuardianAlreadyLinkedError):
        await world.claim(user_id=5)
