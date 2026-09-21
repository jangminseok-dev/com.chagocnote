import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration

_STAFF = {"reservation:write", "customer:write", "record:write", "sales:write"}
_OWNER_ONLY = {"sales:read", "record:delete", "customer:delete", "member:manage", "shop:update"}


async def test_역할과_권한_시드가_설계대로_들어_있다(db_session):
    rows = (
        await db_session.execute(
            text(
                "SELECT r.code, p.code FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id JOIN permissions p ON p.id = rp.permission_id"
            )
        )
    ).all()
    assert {p for r, p in rows if r == "owner"} == _STAFF | _OWNER_ONLY
    assert {p for r, p in rows if r == "staff"} == _STAFF
