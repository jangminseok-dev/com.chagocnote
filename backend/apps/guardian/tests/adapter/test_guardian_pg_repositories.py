"""guardian_links 저장소를 실제 DB 로 본다 — 고객 카드 하나에 살아 있는 연결 하나, 끝난 줄은 남는다."""
import pytest

from guardian.adapter.outbound.pg.guardian_link_pg_repository import GuardianLinkPgRepository
from guardian.domain.errors import GuardianAlreadyLinkedError
from guardian.tests.helpers.builders import kst

pytestmark = pytest.mark.integration

NOW, LATER = kst(11, 13, 10), kst(11, 14, 10)


async def test_연결을_만들고_읽는다(db_session):
    repo = GuardianLinkPgRepository(db_session)
    created = await repo.create(5, 3, 7, "report_link", NOW)
    assert (created.user_id, created.shop_id, created.customer_id, created.verified_by) == (5, 3, 7, "report_link")
    assert (created.created_at, created.ended_at, created.ended_by, created.is_live) == (NOW, None, None, True)
    assert await repo.find_live_for_customer(3, 7) == created
    assert await repo.get_live(5, created.id) == created
    assert await repo.find_live_for_customer(3, 8) is None
    assert await repo.find_live_for_customer(4, 7) is None


async def test_같은_카드에_둘째_연결은_거절되고_트랜잭션은_계속_쓸_수_있다(db_session):
    repo = GuardianLinkPgRepository(db_session)
    await repo.create(5, 3, 7, "report_link", NOW)
    with pytest.raises(GuardianAlreadyLinkedError):
        await repo.create(6, 3, 7, "report_link", NOW)
    other = await repo.create(6, 3, 8, "report_link", NOW)   # 같은 트랜잭션에서 다른 INSERT 가 된다
    assert other.customer_id == 8


async def test_끝낸_뒤에는_다시_이을_수_있고_옛_줄은_남는다(db_session):
    repo = GuardianLinkPgRepository(db_session)
    first = await repo.create(5, 3, 7, "report_link", NOW)
    assert await repo.end(first.id, "guardian", LATER) is True
    assert await repo.end(first.id, "shop", LATER) is False        # 이미 끝난 줄은 다시 끝내지 않는다
    assert await repo.get_live(5, first.id) is None
    second = await repo.create(6, 3, 7, "report_link", LATER)
    assert second.id != first.id
    assert [link.id for link in await repo.list_live_for_user(6)] == [second.id]
    assert await repo.list_live_for_user(5) == []


async def test_남의_계정과_끝난_연결은_get_live_가_없다고_한다(db_session):
    repo = GuardianLinkPgRepository(db_session)
    mine = await repo.create(5, 3, 7, "report_link", NOW)
    assert await repo.get_live(6, mine.id) is None
    assert await repo.get_live(5, mine.id + 100) is None


async def test_내_연결_목록은_이은_순서다(db_session):
    repo = GuardianLinkPgRepository(db_session)
    late = await repo.create(5, 4, 9, "report_link", LATER)
    early = await repo.create(5, 3, 7, "report_link", NOW)
    await repo.create(6, 3, 8, "report_link", NOW)
    assert [link.id for link in await repo.list_live_for_user(5)] == [early.id, late.id]


async def test_탈퇴는_그_계정의_연결만_withdrawn_으로_끝낸다(db_session):
    repo = GuardianLinkPgRepository(db_session)
    a = await repo.create(5, 3, 7, "report_link", NOW)
    b = await repo.create(5, 4, 9, "report_link", NOW)
    other = await repo.create(6, 3, 8, "report_link", NOW)
    assert await repo.end_all_for_user(5, LATER) == 2
    assert await repo.end_all_for_user(5, LATER) == 0
    assert await repo.list_live_for_user(5) == []
    assert await repo.get_live(6, other.id) is not None
    assert await repo.find_live_for_customer(3, 7) is None and await repo.find_live_for_customer(4, 9) is None
    assert {a.id, b.id}.isdisjoint({link.id for link in await repo.list_live_for_user(6)})


async def test_익명화는_그_고객_카드의_연결만_anonymized_로_끝낸다(db_session):
    repo = GuardianLinkPgRepository(db_session)
    await repo.create(5, 3, 7, "report_link", NOW)
    kept = await repo.create(5, 3, 8, "report_link", NOW)
    assert await repo.end_all_for_customer(3, 7, LATER) == 1
    assert await repo.end_all_for_customer(4, 8, LATER) == 0      # 다른 매장의 같은 번호는 건드리지 않는다
    assert [link.id for link in await repo.list_live_for_user(5)] == [kept.id]
