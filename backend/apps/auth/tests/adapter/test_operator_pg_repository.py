import pytest
from sqlalchemy import text

from auth.adapter.outbound.pg.operator_pg_repository import OperatorPgRepository

pytestmark = pytest.mark.integration


async def _user_id(session) -> int:
    return (
        await session.execute(text("INSERT INTO users (display_name) VALUES ('운영자') RETURNING id"))
    ).scalar_one()


async def test_지정하기_전에는_운영자가_아니다(db_session):
    assert await OperatorPgRepository(db_session).is_operator(await _user_id(db_session)) is False


async def test_지정하면_운영자다(db_session):
    repo = OperatorPgRepository(db_session)
    user_id = await _user_id(db_session)
    await repo.grant(user_id)
    assert await repo.is_operator(user_id) is True


async def test_여러_번_지정해도_행은_하나다(db_session):
    repo = OperatorPgRepository(db_session)
    user_id = await _user_id(db_session)
    await repo.grant(user_id)
    await repo.grant(user_id)
    count = (await db_session.execute(text("SELECT count(*) FROM platform_operators"))).scalar_one()
    assert count == 1


async def test_지정을_거두면_운영자가_아니다(db_session):
    repo = OperatorPgRepository(db_session)
    user_id = await _user_id(db_session)
    await repo.grant(user_id)
    await repo.revoke(user_id)
    assert await repo.is_operator(user_id) is False
    await repo.revoke(user_id)   # 여러 번 불러도 같다
