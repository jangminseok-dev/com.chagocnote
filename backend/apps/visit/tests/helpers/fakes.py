"""visit 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
from visit.domain.entities.menu import Menu
from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
from visit.domain.errors import (
    MenuNameTakenError,
    MenuNotFoundError,
    VisitDuplicateError,
    VisitNotFoundError,
)
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS
from visit.tests.helpers.builders import kst


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeSchedule:
    def __init__(self, journal: Journal | None = None, settings=DEFAULT_SETTINGS) -> None:
        self.journal = journal if journal is not None else Journal()
        self.settings = settings
        self.closed: dict[tuple[int, object], ClosedDate] = {}

    async def ensure(self, ctx):
        self.journal.append(("ensure", ctx.shop_id))
        return self.settings

    async def update(self, ctx, settings):
        self.journal.append(("update_settings", ctx.shop_id))
        self.settings = settings
        return settings

    async def list_closed_dates(self, ctx, start, end):
        return sorted(
            (c for (shop, day), c in self.closed.items() if shop == ctx.shop_id and start <= day <= end),
            key=lambda c: c.day,
        )

    async def add_closed_date(self, ctx, day, note):
        self.journal.append(("add_closed_date", day))
        return self.closed.setdefault((ctx.shop_id, day), ClosedDate(day=day, note=note))

    async def delete_closed_date(self, ctx, day):
        self.journal.append(("delete_closed_date", day))
        self.closed.pop((ctx.shop_id, day), None)


class FakeMenus:
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, Menu] = {}
        self._next = 1

    def seed(self, name="목욕", minutes=60, shop_id=1, archived=False) -> Menu:
        menu = Menu(id=self._next, shop_id=shop_id, name=name, default_duration_minutes=minutes,
                    sort_order=self._next, archived_at=kst(9, 1) if archived else None)
        self.rows[menu.id] = menu
        self._next += 1
        return menu

    def _find(self, ctx, menu_id) -> Menu:
        menu = self.rows.get(menu_id)
        if menu is None or menu.shop_id != ctx.shop_id:
            raise MenuNotFoundError("메뉴를 찾을 수 없습니다.")
        return menu

    def _check_name(self, ctx, name, menu_id=None):
        if any(m.name == name and not m.archived and m.shop_id == ctx.shop_id and m.id != menu_id
               for m in self.rows.values()):
            raise MenuNameTakenError("같은 이름의 메뉴가 있습니다.")

    async def list(self, ctx, include_archived):
        return sorted((m for m in self.rows.values() if m.shop_id == ctx.shop_id
                       and (include_archived or not m.archived)), key=lambda m: m.sort_order)

    async def list_active_by_ids(self, ctx, menu_ids):
        return [m for m in self.rows.values() if m.id in menu_ids and m.shop_id == ctx.shop_id
                and not m.archived]

    async def create(self, ctx, name, default_duration_minutes):
        self._check_name(ctx, name)
        menu = self.seed(name=name, minutes=default_duration_minutes, shop_id=ctx.shop_id)
        self.journal.append(("create_menu", name))
        return menu

    async def update(self, ctx, menu_id, name, default_duration_minutes, sort_order):
        current = self._find(ctx, menu_id)
        self._check_name(ctx, name, menu_id)
        self.rows[menu_id] = replace(current, name=name, default_duration_minutes=default_duration_minutes,
                                     sort_order=sort_order)
        self.journal.append(("update_menu", menu_id))
        return self.rows[menu_id]

    async def archive(self, ctx, menu_id):
        current = self._find(ctx, menu_id)
        self.rows[menu_id] = replace(current, archived_at=current.archived_at or kst(9, 23))
        self.journal.append(("archive_menu", menu_id))
        return self.rows[menu_id]


class FamilyRejected(Exception):
    """FakeDirectory 가 가족을 거절할 때 던진다 — 실제로는 customer 의 도메인 오류(404·422)다."""


class FakeDirectory:
    """CustomerDirectoryPort 스텁. families 는 {고객 ID: (매장 ID, {반려동물 ID: 무지개다리 여부})}."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.families: dict[int, tuple[int, dict[int, bool]]] = {}
        self.names: dict[int, str | None] = {}

    def family(self, customer_id=1, pets=(101,), shop_id=1, name="김민지", passed=()) -> None:
        self.families[customer_id] = (shop_id, {p: p in passed for p in pets})
        self.names[customer_id] = name

    async def lock_family(self, ctx, customer_id, pet_ids):
        self.journal.append(("lock_family", customer_id, tuple(pet_ids)))
        shop, pets = self.families.get(customer_id, (None, {}))
        if shop != ctx.shop_id or any(p not in pets or pets[p] for p in pet_ids):
            raise FamilyRejected(customer_id)

    async def briefs(self, ctx, customer_ids, pet_ids):
        customers = {
            c: CustomerBrief(customer_id=c, name=self.names[c], phone_masked="010-12··-5678")
            for c in customer_ids if self.families.get(c, (None,))[0] == ctx.shop_id
        }
        pets = {}
        for c, (shop, family) in self.families.items():
            for p in family:
                if p in pet_ids and shop == ctx.shop_id:
                    pets[p] = PetBrief(pet_id=p, customer_id=c, name=f"아이{p}", species="dog", breed="말티즈",
                                       weight_kg=Decimal("3.2"), passed_away=family[p])
        return FamilyBriefs(customers=customers, pets=pets)

    async def set_last_visit(self, ctx, customer_id, at):
        self.journal.append(("set_last_visit", customer_id, at))


class FakeVisits:
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, Visit] = {}
        self._next = 1

    def seed(self, **fields) -> Visit:
        from visit.tests.helpers.builders import visit

        row = visit(**{"id": self._next, **fields})
        self.rows[row.id] = row
        self._next = max(self._next, row.id) + 1
        return row

    def _clash(self, ctx, customer_id, pet_id, starts_at, ignore=()) -> bool:
        return any(
            v.shop_id == ctx.shop_id and v.status in ACTIVE_STATUSES and v.starts_at == starts_at
            and v.id not in ignore
            and (v.pet_id == pet_id if pet_id is not None else (v.pet_id is None and v.customer_id == customer_id))
            for v in self.rows.values()
        )

    async def create_many(self, ctx, visits):
        if any(self._clash(ctx, n.customer_id, n.pet_id, n.starts_at) for n in visits):
            raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.")
        created = [
            self.seed(shop_id=ctx.shop_id, customer_id=n.customer_id, pet_id=n.pet_id, starts_at=n.starts_at,
                      duration_minutes=n.duration_minutes, status=n.status, started_at=n.started_at,
                      menu_ids=n.menu_ids, memo=n.memo, created_by_member_id=n.created_by_member_id,
                      status_changed_by_member_id=n.created_by_member_id if n.started_at else None)
            for n in visits
        ]
        self.journal.append(("create_visits", [v.id for v in created]))
        return created

    def _owned(self, ctx, visit_id):
        row = self.rows.get(visit_id)
        if row is None or row.shop_id != ctx.shop_id:
            raise VisitNotFoundError("방문을 찾을 수 없습니다.")
        return row

    async def get(self, ctx, visit_id):
        return self._owned(ctx, visit_id)

    async def get_many(self, ctx, visit_ids):
        return [v for v in self._mine(ctx) if v.id in visit_ids]

    async def lock(self, ctx, visit_ids):
        found = [v for v in self._mine(ctx) if v.id in visit_ids]
        self.journal.append(("lock_visits", sorted(v.id for v in found)))
        return found

    async def update_details(self, ctx, visit_id, starts_at, pet_id, duration_minutes, menu_ids, memo):
        current = self._owned(ctx, visit_id)
        if current.is_active and self._clash(ctx, current.customer_id, pet_id, starts_at, ignore=(visit_id,)):
            raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.")
        self.rows[visit_id] = replace(current, starts_at=starts_at, pet_id=pet_id,
                                      duration_minutes=duration_minutes, menu_ids=menu_ids, memo=memo)
        self.journal.append(("update_visit", visit_id))
        return self.rows[visit_id]

    async def reschedule(self, ctx, visit_ids, starts_at):
        moving = [self._owned(ctx, i) for i in visit_ids]
        if any(self._clash(ctx, v.customer_id, v.pet_id, starts_at, ignore=tuple(visit_ids)) for v in moving):
            raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.")
        for v in moving:
            self.rows[v.id] = replace(v, starts_at=starts_at)
        self.journal.append(("reschedule", sorted(visit_ids)))
        return [self.rows[i] for i in sorted(visit_ids)]

    async def apply_changes(self, ctx, changes, member_id):
        for visit_id, change in changes:
            current = self._owned(ctx, visit_id)
            if change.status in ACTIVE_STATUSES and self._clash(
                    ctx, current.customer_id, current.pet_id, current.starts_at, ignore=(visit_id,)):
                raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.")
        for visit_id, change in changes:
            self.rows[visit_id] = replace(
                self.rows[visit_id], status=change.status, started_at=change.started_at,
                completed_at=change.completed_at, canceled_at=change.canceled_at,
                cancel_reason=change.cancel_reason, status_changed_by_member_id=member_id)
        self.journal.append(("apply_changes", [(i, c.status) for i, c in changes]))
        return [self.rows[i] for i, _ in changes]

    async def latest_completed_start(self, ctx, customer_id):
        done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.status == "completed"]
        return max(done) if done else None

    async def list_group(self, ctx, customer_id, starts_at):
        return [v for v in self._mine(ctx) if v.customer_id == customer_id and v.starts_at == starts_at]

    async def last_completed_before(self, ctx, customer_id, pet_id, before):
        found = [v for v in self._mine(ctx) if v.customer_id == customer_id and v.pet_id == pet_id
                 and v.status == "completed" and v.starts_at < before]
        return found[-1] if found else None

    async def last_completed_of_pet(self, ctx, pet_id):
        done = [v for v in self._mine(ctx) if v.pet_id == pet_id and v.status == "completed"]
        return done[-1] if done else None

    async def completed_starts(self, ctx, customer_id, pet_id, limit):
        done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.pet_id == pet_id
                and v.status == "completed"]
        return sorted(done, reverse=True)[:limit]

    async def count_no_show(self, ctx, customer_id):
        return sum(v.customer_id == customer_id and v.status == "no_show" for v in self._mine(ctx))

    def _mine(self, ctx):
        return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id), key=lambda v: (v.starts_at, v.id))

    async def list_between(self, ctx, start, end):
        return [v for v in self._mine(ctx) if start <= v.starts_at < end]

    async def unresolved_before(self, ctx, before):
        found = [v for v in self._mine(ctx) if v.status == "reserved" and v.starts_at < before]
        return len(found), (found[0].starts_at if found else None)

    async def list_occupied(self, ctx, start, end):
        return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id and v.is_active
                       and v.starts_at < end and v.ends_at > start), key=lambda v: (v.starts_at, v.id))
