from hub.app.dtos.membership_summary import MembershipSummary
from tenancy.app.use_cases.list_memberships_interactor import ListMembershipsInteractor


class _StubMembers:
    def __init__(self):
        self.calls = []

    async def list_for_user(self, user_id):
        self.calls.append(user_id)
        return [MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner")]


async def test_유저의_소속_매장을_돌려준다():
    members = _StubMembers()
    result = await ListMembershipsInteractor(members).list_for_user(5)
    assert result == [MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner")]
    assert members.calls == [5]
