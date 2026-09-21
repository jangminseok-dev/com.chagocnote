from datetime import datetime, timezone

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.user_profile import UserProfile
from tenancy.app.dtos.list_members_dto import ListMembersQuery
from tenancy.app.use_cases.list_members_interactor import ListMembersInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.value_objects.role_code import RoleCode

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="staff", permissions=frozenset())


class _StubMembers:
    def __init__(self, members):
        self.members = members
        self.contexts = []

    async def list_active(self, ctx):
        self.contexts.append(ctx)
        return self.members


class _StubUsers:
    def __init__(self):
        self.calls = []

    async def get_profiles(self, user_ids):
        self.calls.append(list(user_ids))
        return {
            1: UserProfile(user_id=1, display_name="사장님", profile_image_url="https://img/1.jpg"),
            2: UserProfile(user_id=2, display_name="직원", profile_image_url=None),
        }


async def test_멤버에_이름과_사진을_붙여_돌려준다():
    members = _StubMembers([
        Member(id=11, shop_id=3, user_id=1, role=RoleCode.OWNER, joined_at=JOINED),
        Member(id=12, shop_id=3, user_id=2, role=RoleCode.STAFF, joined_at=JOINED),
    ])
    users = _StubUsers()
    views = await ListMembersInteractor(members, users).list_members(ListMembersQuery(ctx=CTX))
    assert members.contexts == [CTX]
    assert users.calls == [[1, 2]]
    assert [(v.member_id, v.user_id, v.display_name, v.role) for v in views] == [
        (11, 1, "사장님", "owner"), (12, 2, "직원", "staff"),
    ]
    assert views[0].profile_image_url == "https://img/1.jpg" and views[0].joined_at == JOINED
