"""공개 조회 인터랙터 테스트가 함께 쓰는 무대 — 보낸 알림장 하나와 그 토큰."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hub.app.dtos.shop_profile import ShopProfile
from visit.domain.services.report_rules import hide
from core.link_token import make_token
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakePublicReportLimiter,
    FakeRecords,
    FakeReportRepository,
    FakeReportSettingsRepository,
    FakeShopProfile,
    FakeVisits,
)

KEY = bytes(range(32))
NOW = kst(9, 24, 10)
CLIENT = "203.0.113.7"
SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone="02-123-4567", address=None, timezone="Asia/Seoul",
                   open=True)


class _CountingReports(FakeReportRepository):
    """토큰으로 링크를 찾은 횟수를 센다 — 서명이 틀린 토큰으로는 저장소를 부르지 않는다."""

    def __init__(self, visits) -> None:
        super().__init__(visits)
        self.finds: list[bytes] = []

    async def find(self, public_id):
        self.finds.append(public_id)
        return await super().find(public_id)


class PublicWorld:
    def __init__(self) -> None:
        self.visits, self.settings = FakeVisits(), FakeReportSettingsRepository()
        self.records, self.reports = FakeRecords(self.visits), _CountingReports(self.visits)
        self.menus, self.directory, self.library = FakeMenus(), FakeDirectory(), FakeLibrary()
        self.shops, self.limiter = FakeShopProfile({1: SHOP}), FakePublicReportLimiter()
        self.directory.family(1, pets=(101,))
        for media_id in (51, 52):
            self.library.add(media_id, attached=True)

    async def sent(self, expires_at=kst(10, 23, 15)) -> str:
        """사진 둘(전 51, 후 52 — 52 는 뺐다)과 메모가 있는 완료 방문에 보낸 알림장의 토큰."""
        found = self.visits.seed(status="completed", starts_at=kst(9, 23, 14), started_at=kst(9, 23, 14))
        written = record(found.id, media=((51, "photo", "before", 0), (52, "photo", "after", 0)),
                         weight_kg=Decimal("3.4"), care_note="눈물 자국", internal_note="내부 메모")
        self.records.seed(replace(written, media=hide(written, (52,))))
        report = await self.reports.create(ctx(), found.id, bytes(range(16)), expires_at, kst(9, 23, 15))
        return make_token(report.public_id, KEY)

    def revoke(self) -> None:
        self.reports.rows = [replace(r, revoked_at=kst(9, 23, 16)) for r in self.reports.rows]
