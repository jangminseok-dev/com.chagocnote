"""guardian 의 스텁 — 포트 ABC 를 상속한다(tests/test_fakes_are_ports.py). journal 에 호출이 순서대로 남는다."""
from __future__ import annotations

from dataclasses import replace

from guardian.app.ports.output.claim_limiter_port import ClaimLimiterPort
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.domain.entities.guardian_link import GuardianLink
from guardian.domain.errors import GuardianAlreadyLinkedError
from hub.app.dtos.guardian import ReportLinkTarget
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.report_link_port import ReportLinkPort
from hub.app.ports.shop_profile_port import ShopProfilePort


class FakeLinks(GuardianLinkRepository):
    """guardian_links 스텁 — 고객 카드 하나에 살아 있는 연결은 하나(부분 유일 색인)."""

    def __init__(self, journal: list | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.rows: dict[int, GuardianLink] = {}

    def _live(self):
        return [r for r in self.rows.values() if r.is_live]

    async def create(self, user_id, shop_id, customer_id, verified_by, now):
        if any((r.shop_id, r.customer_id) == (shop_id, customer_id) for r in self._live()):
            raise GuardianAlreadyLinkedError("이미 다른 계정에 연결된 고객입니다.")
        row = GuardianLink(id=len(self.rows) + 1, user_id=user_id, shop_id=shop_id, customer_id=customer_id,
                           verified_by=verified_by, created_at=now, ended_at=None, ended_by=None)
        self.rows[row.id] = row
        self.journal.append(("create_link", user_id, shop_id, customer_id))
        return row

    async def find_live_for_customer(self, shop_id, customer_id):
        return next((r for r in self._live() if (r.shop_id, r.customer_id) == (shop_id, customer_id)), None)

    async def get_live(self, user_id, link_id):
        row = self.rows.get(link_id)
        return row if row is not None and row.is_live and row.user_id == user_id else None

    async def list_live_for_user(self, user_id):
        return sorted((r for r in self._live() if r.user_id == user_id), key=lambda r: (r.created_at, r.id))

    async def end(self, link_id, ended_by, now):
        row = self.rows.get(link_id)
        if row is None or not row.is_live:
            return False
        self.rows[link_id] = replace(row, ended_at=now, ended_by=ended_by)
        self.journal.append(("end_link", link_id, ended_by))
        return True

    async def _end_many(self, rows, ended_by, now):
        for row in rows:
            self.rows[row.id] = replace(row, ended_at=now, ended_by=ended_by)
        return len(rows)

    async def end_all_for_user(self, user_id, now):
        self.journal.append(("end_links_for_user", user_id))
        return await self._end_many([r for r in self._live() if r.user_id == user_id], "withdrawn", now)

    async def end_all_for_customer(self, shop_id, customer_id, now):
        self.journal.append(("end_links_for_customer", shop_id, customer_id))
        return await self._end_many(
            [r for r in self._live() if (r.shop_id, r.customer_id) == (shop_id, customer_id)], "anonymized", now)


class FakeReportLinks(ReportLinkPort):
    """ReportLinkPort 스텁 — 토큰 글자 → 대상. 없는 토큰은 None."""

    def __init__(self, journal: list | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.targets: dict[str, ReportLinkTarget] = {}

    async def resolve(self, token):
        self.journal.append(("resolve_token",))     # 토큰 글자는 남기지 않는다
        return self.targets.get(token)


class FakeActiveUsers(ActiveUserGuardPort):
    """ActiveUserGuardPort 스텁 — inactive 에 든 유저는 활동할 수 없다(탈퇴·정지)."""

    def __init__(self, journal: list | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.inactive: set[int] = set()

    async def lock_active(self, user_id):
        self.journal.append(("lock_user", user_id))
        return user_id not in self.inactive


class FakeClaimLimiter(ClaimLimiterPort):
    """잇기 횟수 제한 스텁 — limit 번까지 통과."""

    def __init__(self, limit: int = 10, journal: list | None = None) -> None:
        self.journal = journal if journal is not None else []
        self.limit = limit
        self.counts: dict[int, int] = {}

    async def allow(self, user_id):
        self.counts[user_id] = self.counts.get(user_id, 0) + 1
        self.journal.append(("count_claim", user_id))
        return self.counts[user_id] <= self.limit


class FakeShops(ShopProfilePort):
    """ShopProfilePort 스텁 — 매장 ID → 공개 정보."""

    def __init__(self, shops: dict[int, ShopProfile] | None = None) -> None:
        self.shops = dict(shops or {})

    async def public_profile(self, shop_id):
        return self.shops.get(shop_id)
