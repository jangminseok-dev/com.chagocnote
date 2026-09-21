"""G2 — 탈퇴와 겹친 연결이 탈퇴한 유저에 신원을 붙이지 못한다. 실제 두 세션으로 확인한다.

`social_identities.user_id`가 `users.id`를 참조하는 외래 키라서, 연결이 유저 행을 명시적으로
잠그지 않아도 신원을 넣는 INSERT 자체가 그 외래 키의 `FOR KEY SHARE` 때문에 탈퇴 세션의
`FOR UPDATE`에 걸려 잠깐 막힌다(다른 두 세션 테스트의 부록 메모에 있는 것과 같은 현상). 그래서
"막혔다가 풀리면 성공하는지"까지 같은 태스크로 이어서 봐야 실제로 판별력이 생긴다 — 막힌 호출을
취소하고 새로 부르면, 명시적 잠금이 없어도 두 번째 호출의 새 조회가 이미 커밋된 탈퇴를 보게 되어
우연히 통과한 것처럼 보인다.
"""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.adapter.outbound.factory.social_provider_factory import SocialProviderFactory
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.app.dtos.link_identity_dto import LinkIdentityCommand
from auth.app.use_cases.link_identity_interactor import LinkIdentityInteractor
from auth.domain.errors import UserNotFoundError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile
from tests.integration.support import FakeKakaoStrategy

pytestmark = pytest.mark.integration


def _link(session, user_id, resolver):
    interactor = LinkIdentityInteractor(providers=resolver, users=UserPgRepository(session))
    return interactor.link(
        LinkIdentityCommand(user_id=user_id, provider="kakao", token="DubuKakao", authorization_code=None, nonce=None)
    )


async def test_탈퇴가_유저_행을_쥔_동안_연결은_기다리고_탈퇴한_뒤에는_거절된다(db_engine):
    resolver = SocialProviderFactory({Provider.KAKAO: FakeKakaoStrategy()})
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        user = await UserPgRepository(setup).create_with_identity(
            SocialProfile(Provider.DEV, "linking-leaver", None, "떠나는 사람", None, None)
        )
        await setup.commit()

    async with factory() as withdrawing, factory() as linking:
        users = UserPgRepository(withdrawing)
        assert (await users.lock(user.id)).id == user.id   # 탈퇴가 맨 앞에서 하는 일
        await users.anonymize(user.id)

        # 제공자 검증(잠금 전)은 끝나지만, 유저 행 잠금에서 기다린다. 취소하지 않고 그대로 들고 있다가
        # 탈퇴가 커밋된 뒤에 풀려나는 바로 그 호출이 무엇을 하는지 본다.
        link_task = asyncio.create_task(_link(linking, user.id, resolver))
        await asyncio.sleep(0.2)   # 연결이 유저 행(또는 외래 키)에서 멈출 시간을 준다
        assert not link_task.done()

        await withdrawing.commit()
        with pytest.raises(UserNotFoundError):
            await asyncio.wait_for(link_task, timeout=1)

    async with factory() as check:
        count = (
            await check.execute(
                text("SELECT count(*) FROM social_identities WHERE user_id = :id"), {"id": user.id}
            )
        ).scalar_one()
        assert count == 1   # dev 신원만 남는다 — 풀려난 연결이 카카오 신원을 붙이지 못했다.
