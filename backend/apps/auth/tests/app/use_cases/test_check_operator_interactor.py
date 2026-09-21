from auth.app.use_cases.check_operator_interactor import CheckOperatorInteractor


class _StubOperators:
    def __init__(self, operator_ids):
        self.operator_ids = set(operator_ids)

    async def is_operator(self, user_id):
        return user_id in self.operator_ids


async def test_지정된_유저는_운영자다():
    assert await CheckOperatorInteractor(_StubOperators([5])).is_operator(5) is True


async def test_지정되지_않은_유저는_운영자가_아니다():
    assert await CheckOperatorInteractor(_StubOperators([5])).is_operator(6) is False
