import asyncio

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher
from auth.adapter.outbound.orm.user_orm import UserOrm
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.domain.errors import IdentityAlreadyLinkedError, ProviderAlreadyLinkedError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile

pytestmark = pytest.mark.integration


def _profile(**overrides):
    base = dict(
        provider=Provider.KAKAO, provider_user_id="kakao-100", email="a@example.com",
        display_name="두부 보호자", profile_image_url=None, provider_refresh_token=None,
    )
    return SocialProfile(**{**base, **overrides})


def _repo(session):
    return UserPgRepository(session, FernetCipher(Fernet.generate_key().decode()))


async def test_신원으로_유저를_만들고_다시_찾는다(db_session):
    repo = _repo(db_session)
    created = await repo.create_with_identity(_profile())
    found = await repo.find_by_identity(Provider.KAKAO, "kakao-100")
    assert found is not None and found.id == created.id
    assert found.display_name == "두부 보호자"


async def test_없는_신원은_None_이다(db_session):
    assert await _repo(db_session).find_by_identity(Provider.GOOGLE, "nobody") is None


async def test_이름이_없는_프로필은_기본_이름으로_만든다(db_session):
    user = await _repo(db_session).create_with_identity(_profile(display_name=None))
    assert user.display_name == "이름 없음"


async def test_긴_이름은_50자로_잘라_저장한다(db_session):
    user = await _repo(db_session).create_with_identity(_profile(display_name="가" * 60))
    assert len(user.display_name) == 50


async def test_연결된_로그인_수단_목록을_돌려준다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile())
    identities = await repo.list_identities(user.id)
    assert [i.provider for i in identities] == [Provider.KAKAO]


async def test_제공자_리프레시_토큰은_암호화해서_저장한다(db_session):
    repo = _repo(db_session)
    await repo.create_with_identity(
        _profile(provider=Provider.APPLE, provider_user_id="apple-1", provider_refresh_token="plain-token")
    )
    stored = (
        await db_session.execute(
            text("SELECT provider_refresh_token_enc FROM social_identities WHERE provider = 'apple'")
        )
    ).scalar_one()
    assert stored and stored != "plain-token"


async def test_여러_유저를_ID_로_한_번에_읽는다(db_session):
    repo = _repo(db_session)
    first = await repo.create_with_identity(_profile(provider_user_id="kakao-1", display_name="하나"))
    second = await repo.create_with_identity(_profile(provider_user_id="kakao-2", display_name="둘"))
    await repo.create_with_identity(_profile(provider_user_id="kakao-3", display_name="셋"))
    users = await repo.list_by_ids([second.id, first.id])
    assert sorted(u.display_name for u in users) == ["둘", "하나"]
    assert await repo.list_by_ids([]) == []


async def test_암호화_도구_없이_조립하면_제공자_토큰을_저장하지_못한다(db_session):
    repo = UserPgRepository(db_session)
    with pytest.raises(RuntimeError, match="암호화"):
        await repo.create_with_identity(
            _profile(provider=Provider.APPLE, provider_user_id="apple-2", provider_refresh_token="plain")
        )


async def test_암호화_도구_없이도_토큰_없는_프로필은_저장하고_읽는다(db_session):
    repo = UserPgRepository(db_session)
    created = await repo.create_with_identity(_profile(provider_user_id="kakao-200"))
    assert (await repo.get(created.id)).display_name == "두부 보호자"
    assert await repo.get(999999) is None


async def test_이미_있는_신원으로_만들면_IdentityAlreadyLinkedError_이고_세션은_계속_쓸_수_있다(db_session):
    repo = _repo(db_session)
    first = await repo.create_with_identity(_profile())
    with pytest.raises(IdentityAlreadyLinkedError):
        await repo.create_with_identity(_profile(display_name="늦은 요청"))
    # 진 쪽이 만들려던 유저 행도 함께 되돌아간다.
    count = (await db_session.execute(text("SELECT count(*) FROM users"))).scalar_one()
    assert count == 1
    assert (await repo.find_by_identity(Provider.KAKAO, "kakao-100")).id == first.id


async def test_비어_있는_제공자_토큰만_채운다(db_session):
    repo = _repo(db_session)
    await repo.create_with_identity(_profile(provider=Provider.APPLE, provider_user_id="apple-9"))

    async def stored():
        return (
            await db_session.execute(
                text("SELECT provider_refresh_token_enc FROM social_identities WHERE provider_user_id = 'apple-9'")
            )
        ).scalar_one()

    assert await stored() is None
    await repo.fill_provider_refresh_token(Provider.APPLE, "apple-9", "first-token")
    filled = await stored()
    assert filled and filled != "first-token"
    await repo.fill_provider_refresh_token(Provider.APPLE, "apple-9", "second-token")
    assert await stored() == filled


async def test_로그인_수단을_더_붙이면_붙인_순서대로_나온다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile())
    await repo.add_identity(user.id, _profile(provider=Provider.APPLE, provider_user_id="apple-1",
                                              provider_refresh_token="apple-refresh"))
    assert [i.provider for i in await repo.list_identities(user.id)] == [Provider.KAKAO, Provider.APPLE]
    found = await repo.find_by_identity(Provider.APPLE, "apple-1")
    assert found.id == user.id


async def test_다른_유저의_신원은_붙일_수_없다(db_session):
    """G3"""
    repo = _repo(db_session)
    await repo.create_with_identity(_profile(provider_user_id="kakao-owned"))
    me = await repo.create_with_identity(_profile(provider=Provider.GOOGLE, provider_user_id="google-me"))
    with pytest.raises(IdentityAlreadyLinkedError):
        await repo.add_identity(me.id, _profile(provider_user_id="kakao-owned"))
    assert [i.provider for i in await repo.list_identities(me.id)] == [Provider.GOOGLE]


async def test_같은_제공자의_신원을_둘_붙일_수_없다(db_session):
    """G4"""
    repo = _repo(db_session)
    me = await repo.create_with_identity(_profile(provider_user_id="kakao-first"))
    with pytest.raises(ProviderAlreadyLinkedError):
        await repo.add_identity(me.id, _profile(provider_user_id="kakao-second"))
    assert len(await repo.list_identities(me.id)) == 1


async def test_이미_내_계정에_붙어_있는_바로_그_신원을_다시_붙이면_PROVIDER_ALREADY_LINKED_다(db_session):
    """두 유일 제약이 동시에 걸릴 때, 자기 자신에게 탈퇴를 권하는 오안내를 하지 않는다."""
    repo = _repo(db_session)
    me = await repo.create_with_identity(_profile())
    with pytest.raises(ProviderAlreadyLinkedError):
        await repo.add_identity(me.id, _profile())
    assert len(await repo.list_identities(me.id)) == 1


async def test_연결을_끊을_신원을_복호화한_토큰과_함께_돌려준다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile())
    await repo.add_identity(user.id, _profile(provider=Provider.APPLE, provider_user_id="apple-1",
                                              provider_refresh_token="apple-refresh"))
    revocations = await repo.list_revocations(user.id)
    # 토큰 원문은 실패 메시지에도 찍히면 안 되니 불리언으로만 비교한다.
    assert [(r.provider, r.provider_user_id) for r in revocations] == [
        (Provider.KAKAO, "kakao-100"), (Provider.APPLE, "apple-1"),
    ]
    assert (revocations[0].provider_refresh_token is None) is True
    assert (revocations[1].provider_refresh_token == "apple-refresh") is True
    assert "apple-refresh" not in repr(revocations[1])


async def test_신원_하나를_지우면_그_수단으로는_찾을_수_없다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile())
    await repo.add_identity(user.id, _profile(provider=Provider.GOOGLE, provider_user_id="google-1"))
    await repo.delete_identity(user.id, Provider.KAKAO)
    assert [i.provider for i in await repo.list_identities(user.id)] == [Provider.GOOGLE]
    assert await repo.find_by_identity(Provider.KAKAO, "kakao-100") is None


async def test_익명화하고_신원을_모두_지우면_같은_소셜_계정으로_새로_가입할_수_있다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile(profile_image_url="https://img/1.jpg"))
    await db_session.execute(
        text("UPDATE users SET phone = '010-0000-0000', suspended_at = now() WHERE id = :id"),
        {"id": user.id},
    )
    await repo.anonymize(user.id)
    await repo.delete_identities(user.id)

    gone = await repo.lock(user.id)
    assert (gone.display_name, gone.profile_image_url, gone.phone) == ("탈퇴한 사용자", None, None)
    assert gone.is_deleted is True
    assert gone.is_suspended is True  # 익명화는 정지 상태를 지우지 않는다.
    assert await repo.list_identities(user.id) == []
    again = await repo.create_with_identity(_profile())
    assert again.id != user.id


async def test_유저_행_잠금은_같은_유저의_다른_요청을_기다리게_한다(db_engine):
    """G1·G2·H5 — 계정을 바꾸는 요청들이 유저 단위로 직렬화된다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        user = await _repo(setup).create_with_identity(_profile())
        other = await _repo(setup).create_with_identity(_profile(provider_user_id="kakao-other"))
        await setup.commit()

    async with factory() as one, factory() as two:
        assert (await _repo(one).lock(user.id)).id == user.id
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_repo(two).lock(user.id), timeout=0.5)
        await two.rollback()
        # 다른 유저는 막지 않는다.
        assert (await asyncio.wait_for(_repo(two).lock(other.id), timeout=0.5)).id == other.id
        await two.rollback()

        await _repo(one).anonymize(user.id)
        await one.commit()
        # 기다리던 쪽은 잠금이 풀리자마자 손에 넣는다 — 직렬화를 증명한다.
        # (최신 값을 보는지는 populate_existing 전용 테스트가 따로 증명한다.)
        assert (await asyncio.wait_for(_repo(two).lock(user.id), timeout=0.5)).is_deleted is True
        await two.rollback()


async def test_잠근_뒤에는_같은_세션이_이미_읽어_둔_값이_아니라_최신_값을_본다(db_engine):
    """populate_existing 이 없으면 identity map 에 남은 옛 값을 그대로 돌려준다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        user = await _repo(setup).create_with_identity(_profile())
        await setup.commit()

    async with factory() as one, factory() as two:
        # 세션 two 의 identity map 에 옛 값을 지역 변수로 붙들어 GC 되지 않게 한다.
        held = await two.get(UserOrm, user.id)
        assert held.display_name == "두부 보호자"

        await _repo(one).anonymize(user.id)
        await one.commit()

        locked = await _repo(two).lock(user.id)
        assert locked.is_deleted is True
        assert locked.display_name == "탈퇴한 사용자"


async def test_없는_유저를_잠그면_None_이다(db_session):
    assert await _repo(db_session).lock(999999) is None
