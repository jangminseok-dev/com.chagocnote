from auth.app.dtos.token_dto import AccessToken
from auth.app.services.session_issuer import SessionIssuer


class _StubIssuer:
    def issue_access(self, user_id):
        return AccessToken(token=f"access-for-{user_id}", expires_in=900)


class _StubStore:
    def __init__(self, generation=0):
        self.generation = generation
        self.saved = []

    async def current_generation(self, user_id):
        return self.generation

    async def save(self, token, user_id, generation):
        self.saved.append((token, user_id, generation))


async def test_로그인은_현재_세대로_리프레시_토큰을_저장한다():
    store = _StubStore(generation=3)
    pair = await SessionIssuer(_StubIssuer(), store).issue(5)
    assert (pair.access_token, pair.expires_in) == ("access-for-5", 900)
    assert store.saved == [(pair.refresh_token, 5, 3)]
    assert pair.refresh_token.startswith("5.")


async def test_갱신은_꺼낼_때_받은_세대로_저장한다():
    store = _StubStore(generation=9)
    pair = await SessionIssuer(_StubIssuer(), store).issue(5, generation=2)
    assert store.saved == [(pair.refresh_token, 5, 2)]


async def test_리프레시_토큰은_매번_다르다():
    issuer = SessionIssuer(_StubIssuer(), _StubStore())
    assert (await issuer.issue(5)).refresh_token != (await issuer.issue(5)).refresh_token
