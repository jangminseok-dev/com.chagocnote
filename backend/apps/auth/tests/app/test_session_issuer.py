from auth.app.dtos.token_dto import AccessToken
from auth.app.services.session_issuer import SessionIssuer


class _StubIssuer:
    def __init__(self):
        self.seen = []

    def issue_access(self, user_id, *, auth_time=None, fresh_login=False):
        self.seen.append((user_id, auth_time, fresh_login))
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


async def test_기본_발급은_로그인_시각을_찍지_않는다():
    issuer = _StubIssuer()
    await SessionIssuer(issuer, _StubStore()).issue(5, generation=2)
    assert issuer.seen == [(5, None, False)]


async def test_새_로그인과_물려받은_시각을_발급기에_그대로_넘긴다():
    issuer = _StubIssuer()
    sessions = SessionIssuer(issuer, _StubStore())
    await sessions.issue(5, fresh_login=True)
    await sessions.issue(5, auth_time=1_700_000_000)
    assert issuer.seen == [(5, None, True), (5, 1_700_000_000, False)]


class _TtlIssuer(_StubIssuer):
    def issue_access(self, user_id, *, auth_time=None, fresh_login=False, ttl_seconds=None):
        self.seen.append((user_id, auth_time, fresh_login, ttl_seconds))
        return AccessToken(token=f"access-for-{user_id}", expires_in=ttl_seconds or 900)


async def test_웹_세션은_30분짜리_액세스_토큰만_내주고_리프레시_저장소를_건드리지_않는다():
    issuer, store = _TtlIssuer(), _StubStore()
    pair = await SessionIssuer(issuer, store).issue_web(5)
    assert (pair.access_token, pair.refresh_token, pair.expires_in) == ("access-for-5", None, 1800)
    assert store.saved == []
    assert issuer.seen == [(5, None, True, 1800)]   # 로그인 시각을 찍는다
