from auth.app.dtos.logout_dto import LogoutCommand
from auth.app.use_cases.logout_interactor import LogoutInteractor


class _StubStore:
    def __init__(self):
        self.revoked = []

    async def revoke(self, token):
        self.revoked.append(token)


async def test_리프레시_토큰을_폐기한다():
    store = _StubStore()
    await LogoutInteractor(store).logout(LogoutCommand("my-refresh"))
    assert store.revoked == ["my-refresh"]


async def test_같은_토큰으로_두_번_로그아웃해도_실패하지_않는다():
    store = _StubStore()
    interactor = LogoutInteractor(store)
    await interactor.logout(LogoutCommand("my-refresh"))
    await interactor.logout(LogoutCommand("my-refresh"))
    assert store.revoked == ["my-refresh", "my-refresh"]
