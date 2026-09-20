from auth.app.dtos.token_dto import AccessToken
from auth.app.services.session_issuer import SessionIssuer


class _StubIssuer:
    def issue_access(self, user_id):
        return AccessToken(token=f"access-for-{user_id}", expires_in=900)


class _StubStore:
    def __init__(self):
        self.saved = []

    async def save(self, token, user_id):
        self.saved.append((token, user_id))


async def test_액세스_토큰과_새_리프레시_토큰을_함께_발급하고_리프레시를_저장한다():
    store = _StubStore()
    pair = await SessionIssuer(_StubIssuer(), store).issue(5)
    assert pair.access_token == "access-for-5"
    assert pair.expires_in == 900
    assert store.saved == [(pair.refresh_token, 5)]
    assert len(pair.refresh_token) >= 43


async def test_리프레시_토큰은_매번_다르다():
    issuer = SessionIssuer(_StubIssuer(), _StubStore())
    assert (await issuer.issue(5)).refresh_token != (await issuer.issue(5)).refresh_token
