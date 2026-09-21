import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text

from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
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
