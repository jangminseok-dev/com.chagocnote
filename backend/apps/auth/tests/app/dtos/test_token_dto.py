import pytest

from auth.app.dtos.link_identity_dto import LinkIdentityCommand
from auth.app.dtos.logout_dto import LogoutCommand
from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.dtos.social_login_dto import SocialLoginCommand
from auth.app.dtos.token_dto import AccessToken, TokenPair
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile

SECRET = "sesame-value"


def test_repr에는_접근_토큰도_리프레시_토큰도_찍히지_않는다():
    tokens = TokenPair("secret-access-token", "5.secret-refresh-token", 900)
    text = repr(tokens)
    # 비교 결과를 지역 변수에 먼저 담는다. pytest 의 단언 재작성은 assert 문 안의 비교 노드까지
    # 그대로 풀어 찍으므로, 여기서 직접 비교하면 실패 출력에 원문 토큰이 찍힌다.
    access_missing = "secret-access-token" not in text
    refresh_missing = "secret-refresh-token" not in text
    assert access_missing and refresh_missing
    assert text == "TokenPair(expires_in=900)"


# 비밀값을 담는 자료형과, 그 값을 넣어 만드는 방법. 기본 repr 이 그대로 로그·예외 메시지에 실려
# 나가지 않는지 한 곳에서 고정한다.
_CARRIERS = [
    ("AccessToken", lambda: AccessToken(token=SECRET, expires_in=900)),
    ("SocialCredentials", lambda: SocialCredentials(token=SECRET, authorization_code=SECRET)),
    (
        "SocialProfile",
        lambda: SocialProfile(Provider.APPLE, "apple-1", None, "두부 보호자", None, SECRET),
    ),
    (
        "SocialLoginCommand",
        lambda: SocialLoginCommand(
            provider="apple", token=SECRET, authorization_code=SECRET,
            nonce="nonce", display_name=None,
        ),
    ),
    (
        "LinkIdentityCommand",
        lambda: LinkIdentityCommand(
            user_id=5, provider="apple", token=SECRET, authorization_code=SECRET, nonce="nonce"
        ),
    ),
    ("RefreshTokenCommand", lambda: RefreshTokenCommand(refresh_token=SECRET)),
    ("LogoutCommand", lambda: LogoutCommand(refresh_token=SECRET)),
    ("IdentityRevocation", lambda: IdentityRevocation(Provider.APPLE, "apple-1", SECRET)),
]


@pytest.mark.parametrize("name, make", _CARRIERS, ids=[name for name, _ in _CARRIERS])
def test_비밀값을_담는_자료형의_repr에는_값이_없다(name, make):
    # 값 자체를 단언에 쓰지 않는다 — 실패 출력에 원문이 실리지 않게 지역 불리언으로 비교한다.
    secret_missing = SECRET not in repr(make())
    assert secret_missing, f"{name} 의 repr 에 비밀값이 찍힌다"
