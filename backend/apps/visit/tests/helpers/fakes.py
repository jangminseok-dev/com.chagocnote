"""visit 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다.

스텁은 포트 ABC 를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 AttributeError 로 늦게 잡히는 대신
인스턴스를 만드는 순간(TypeError) 잡힌다. `apps/visit/tests/test_fakes_are_ports.py`가 이를 확인한다.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hub.app.dtos.care_facts import CareFacts, PetCareFact
from hub.app.dtos.customer_contact import CustomerContact
from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
from hub.app.dtos.media_urls import MediaUrls
from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.dtos.visit_events import VisitEvent
from hub.app.errors import (
    FamilyNotFoundError,
    FamilyPetNotFoundError,
    FamilyPetPassedAwayError,
    MediaClaimAlreadyAttachedError,
    MediaClaimNotFoundError,
    MediaClaimNotReadyError,
)
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.report_target_dto import ReportTarget
from visit.app.ports.output.menu_repository import MenuRepository
from hub.app.ports.public_limiter_port import PublicLimiterPort
from visit.app.dtos.guardian_report_dto import SentReport
from visit.app.ports.output.guardian_report_repository import GuardianReportRepository
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.sales_goal_repository import SalesGoalRepository
from visit.app.ports.output.sales_repository import SalesRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_check_repository import VisitCheckRepository
from visit.app.ports.output.visit_feed_repository import FeedPage, VisitFeedRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.domain.value_objects.sales import (
    DaySales,
    MenuSales,
    PetVisits,
    RemainingBookings,
    SalesTotals,
    SalesVisitRow,
)
from visit.domain.entities.menu import Menu
from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
from visit.domain.entities.visit_record import VisitRecord
from visit.domain.entities.visit_report import VisitReport
from visit.domain.errors import (
    MenuNameTakenError,
    MenuNotFoundError,
    VisitDuplicateError,
    VisitNotFoundError,
)
from visit.domain.services.report_rules import hide
from visit.domain.state.visit_status import STARTED_STATUSES
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.revisit_settings import DEFAULT_REVISIT_SETTINGS, RevisitSettings
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings
from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS
from visit.tests.helpers.builders import kst


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeSchedule(ScheduleRepository):
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


class FakeMenus(MenuRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, Menu] = {}
        self._next = 1

    def seed(self, name="목욕", minutes=60, shop_id=1, archived=False, price=None) -> Menu:
        menu = Menu(id=self._next, shop_id=shop_id, name=name, default_duration_minutes=minutes,
                    sort_order=self._next, archived_at=kst(9, 1) if archived else None, price=price)
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

    async def list_by_ids(self, ctx, menu_ids):
        return [m for m in self.rows.values() if m.id in menu_ids and m.shop_id == ctx.shop_id]

    async def create(self, ctx, name, default_duration_minutes, price):
        self._check_name(ctx, name)
        menu = self.seed(name=name, minutes=default_duration_minutes, shop_id=ctx.shop_id, price=price)
        self.journal.append(("create_menu", name))
        return menu

    async def update(self, ctx, menu_id, name, default_duration_minutes, sort_order, price):
        current = self._find(ctx, menu_id)
        self._check_name(ctx, name, menu_id)
        self.rows[menu_id] = replace(current, name=name, default_duration_minutes=default_duration_minutes,
                                     sort_order=sort_order, price=price)
        self.journal.append(("update_menu", menu_id))
        return self.rows[menu_id]

    async def archive(self, ctx, menu_id):
        current = self._find(ctx, menu_id)
        self.rows[menu_id] = replace(current, archived_at=current.archived_at or kst(9, 23))
        self.journal.append(("archive_menu", menu_id))
        return self.rows[menu_id]


class FakeDirectory(CustomerDirectoryPort):
    """CustomerDirectoryPort 스텁. families 는 {고객 ID: (매장 ID, {반려동물 ID: 무지개다리 여부})}."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.families: dict[int, tuple[int, dict[int, bool]]] = {}
        self.names: dict[int, str | None] = {}
        self.pet_names: dict[int, str | None] = {}   # 없는 아이는 "아이{ID}". 익명화한 가족이면 None 을 넣는다
        self.candidates: list = []
        self.contacts: dict[int, CustomerContact] = {}   # family() 가 기본값을 넣는다. 익명화를 흉내 내려면 뺀다
        self.cautions: dict = {}     # 고객 ID → CautionFact (확인할 것)
        self.pet_facts: dict = {}    # 반려동물 ID → PetCareFact. 없으면 나이·지병·동의가 없는 아이다
        self.care_calls: list = []   # care_facts 가 받은 (고객 ID 들, 반려동물 ID 들, 오늘)
        self.revisits: dict = {}     # 반려동물 ID → PetRevisitFact(⑬). 없으면 직접 정한 주기·안내한 날이 없다
        self.revisit_calls: list = []   # revisit_facts 가 받은 반려동물 ID 들

    def family(self, customer_id=1, pets=(101,), shop_id=1, name="김민지", passed=()) -> None:
        self.families[customer_id] = (shop_id, {p: p in passed for p in pets})
        self.names[customer_id] = name
        self.contacts[customer_id] = CustomerContact(customer_id=customer_id, name=name, phone="01012345678",
                                                     marketing_consent=True)

    async def first_pets(self, ctx, customer_ids):
        raise NotImplementedError   # visit 은 쓰지 않는다

    async def care_facts(self, ctx, customer_ids, pet_ids, today):
        self.care_calls.append((tuple(customer_ids), tuple(pet_ids), today))
        known = frozenset(c for c in customer_ids if self.families.get(c, (None,))[0] == ctx.shop_id)
        pets = {}
        for c in known:
            for p, passed in self.families[c][1].items():
                if p in pet_ids:
                    pets[p] = self.pet_facts.get(p) or PetCareFact(
                        pet_id=p, customer_id=c, birth_date=None, birth_year=None, conditions=(),
                        consent_on=None, passed_away=passed,
                    )
        return CareFacts(
            known_customers=known,
            cautions={c: fact for c, fact in self.cautions.items() if c in known},
            pets=pets,
        )

    async def lock_family(self, ctx, customer_id, pet_ids):
        """실제 구현(customer)과 같은 허브 오류를 같은 조건에서 던진다 — 포트 계약이 곧 스텁의 계약이다."""
        self.journal.append(("lock_family", customer_id, tuple(pet_ids)))
        shop, pets = self.families.get(customer_id, (None, {}))
        if shop != ctx.shop_id:
            raise FamilyNotFoundError("고객을 찾을 수 없습니다.")
        for pet_id in pet_ids:
            if pet_id not in pets:
                raise FamilyPetNotFoundError("반려동물을 찾을 수 없습니다.")
            if pets[pet_id]:
                raise FamilyPetPassedAwayError("무지개다리를 건넌 아이에게는 예약을 잡을 수 없습니다.")

    async def briefs(self, ctx, customer_ids, pet_ids):
        customers = {
            c: CustomerBrief(customer_id=c, name=self.names[c], phone_masked="010-12··-5678")
            for c in customer_ids if self.families.get(c, (None,))[0] == ctx.shop_id
        }
        pets = {}
        for c, (shop, family) in self.families.items():
            for p in family:
                if p in pet_ids and shop == ctx.shop_id:
                    pets[p] = PetBrief(pet_id=p, customer_id=c, name=self.pet_names.get(p, f"아이{p}"),
                                       species="dog", breed="말티즈", weight_kg=Decimal("3.2"),
                                       passed_away=family[p])
        return FamilyBriefs(customers=customers, pets=pets)

    async def set_last_visit(self, ctx, customer_id, at):
        self.journal.append(("set_last_visit", customer_id, at))

    async def set_pet_weight(self, ctx, pet_id, weight_kg):
        self.journal.append(("set_pet_weight", pet_id, weight_kg))

    async def find_draft_candidates(self, ctx, words):
        """카톡 초안 후보 — 미리 넣어 둔 후보(self.candidates)를 그대로 준다."""
        self.journal.append(("find_draft_candidates", tuple(words)))
        return list(self.candidates)

    async def contact(self, ctx, customer_id):
        if self.families.get(customer_id, (None,))[0] != ctx.shop_id:
            return None
        return self.contacts.get(customer_id)

    async def revisit_facts(self, ctx, pet_ids):
        self.revisit_calls.append(tuple(pet_ids))
        return {p: self.revisits[p] for p in pet_ids if p in self.revisits}


class FakeVisits(
    VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository, VisitFeedRepository,
):
    """visits 표 스텁 — pg 구현처럼 여섯 포트(찾기·잠금, 쓰기, 이력, 원장, 게시판, 피드)를 한 객체가 다 낸다.

    피드 커서는 마지막으로 준 방문 ID 를 글자로 쓴다(pg 구현의 모양과 다르다 — 부르는 쪽은 커서를 열어 보지 않는다).
    """

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

    async def latest_completed_start_excluding(self, ctx, customer_id, pet_id, exclude_visit_id):
        done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.pet_id == pet_id
                and v.status == "completed" and v.id != exclude_visit_id]
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

    async def latest_started_of_pet(self, ctx, pet_id):
        started = [v for v in self._mine(ctx) if v.pet_id == pet_id and v.status in STARTED_STATUSES]
        return max(started, key=lambda v: (v.starts_at, v.id)).id if started else None

    async def completed_starts(self, ctx, customer_id, pet_id, limit):
        done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.pet_id == pet_id
                and v.status == "completed"]
        return sorted(done, reverse=True)[:limit]

    async def completed_days(self, ctx, pet_ids, per_pet):
        from visit.domain.services.visit_schedule import local_date

        days: dict[int, list] = {}
        done = sorted((v for v in self._mine(ctx) if v.pet_id in pet_ids and v.status == "completed"),
                      key=lambda v: v.starts_at, reverse=True)
        for v in done:
            if len(days.setdefault(v.pet_id, [])) < per_pet:
                days[v.pet_id].append(local_date(v.starts_at, ctx.timezone))
        return days

    def _upcoming(self, v, since) -> bool:
        return v.status == "in_progress" or (v.status == "reserved" and v.starts_at >= since)

    async def pets_with_upcoming(self, ctx, pet_ids, since):
        return {v.pet_id for v in self._mine(ctx) if v.pet_id in pet_ids and self._upcoming(v, since)}

    async def revisit_candidates(self, ctx, today, since):
        from visit.domain.services.visit_schedule import local_date
        from visit.domain.value_objects.revisit import RevisitCandidate

        self.revisit_calls = getattr(self, "revisit_calls", 0) + 1
        latest: dict[int, Visit] = {}
        for v in self._mine(ctx):
            if v.pet_id is not None and v.status == "completed":
                if v.pet_id not in latest or (v.starts_at, v.id) > (latest[v.pet_id].starts_at, latest[v.pet_id].id):
                    latest[v.pet_id] = v
        busy = {v.pet_id for v in self._mine(ctx) if self._upcoming(v, since)}
        found = [RevisitCandidate(pet_id=p, last_visit_id=v.id, last_day=local_date(v.starts_at, ctx.timezone))
                 for p, v in latest.items() if p not in busy]
        return sorted((c for c in found if (today - c.last_day).days <= 365), key=lambda c: (c.last_day, c.pet_id))

    async def pet_has_visits(self, ctx, pet_id, active_only):
        return any(v.pet_id == pet_id and (v.is_active or not active_only) for v in self._mine(ctx))

    async def customer_has_active(self, ctx, customer_id):
        return any(v.customer_id == customer_id and v.is_active for v in self._mine(ctx))

    async def list_active_from(self, ctx, customer_id, since, limit):
        return [v for v in self._mine(ctx) if v.customer_id == customer_id and v.is_active
                and v.starts_at >= since][:limit]

    async def clear_memos(self, ctx, customer_id):
        for v in self._mine(ctx):
            if v.customer_id == customer_id:
                self.rows[v.id] = replace(v, memo=None)
        self.journal.append(("clear_memos", customer_id))

    async def count_no_show(self, ctx, customer_id):
        return sum(v.customer_id == customer_id and v.status == "no_show" for v in self._mine(ctx))

    def _mine(self, ctx):
        return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id), key=lambda v: (v.starts_at, v.id))

    async def list_between(self, ctx, start, end):
        return [v for v in self._mine(ctx) if start <= v.starts_at < end]

    async def unresolved_before(self, ctx, before):
        found = [v for v in self._mine(ctx) if v.status == "reserved" and v.starts_at < before]
        return len(found), (found[0].starts_at if found else None)

    async def list_completed(self, ctx, cursor, limit, pet_id):
        done = sorted((v for v in self._mine(ctx) if v.status == "completed" and (pet_id is None or v.pet_id == pet_id)),
                      key=lambda v: (v.completed_at, v.id), reverse=True)
        if cursor is not None:
            after = self.rows[int(cursor)]
            done = [v for v in done if (v.completed_at, v.id) < (after.completed_at, after.id)]
        page = done[:limit]
        return FeedPage(visits=page, next_cursor=str(page[-1].id) if len(done) > limit else None)

    async def list_occupied(self, ctx, start, end):
        return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id and v.is_active
                       and v.starts_at < end and v.ends_at > start), key=lambda v: (v.starts_at, v.id))


class FakeRecords(VisitRecordRepository):
    """visit_records 스텁. 방문의 매장은 visits 스텁에서 본다(pg 구현이 visits 와 조인하는 것처럼)."""

    def __init__(self, visits: FakeVisits, journal: Journal | None = None) -> None:
        self.visits = visits
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, VisitRecord] = {}

    def seed(self, record: VisitRecord) -> VisitRecord:
        self.rows[record.visit_id] = record
        return record

    async def get(self, ctx, visit_id):
        visit = self.visits.rows.get(visit_id)
        if visit is None or visit.shop_id != ctx.shop_id:
            return None
        return self.rows.get(visit_id)

    async def list_many(self, ctx, visit_ids):
        return {i: self.rows[i] for i in visit_ids if i in self.rows and self.visits.rows[i].shop_id == ctx.shop_id}

    async def latest_with_media(self, ctx, pet_ids):
        found = {}
        for visit in sorted(self.visits._mine(ctx), key=lambda v: (v.starts_at, v.id)):
            if visit.pet_id in pet_ids and visit.status == "completed" and visit.id in self.rows \
                    and self.rows[visit.id].media:
                found[visit.pet_id] = visit.id
        return found

    async def clear_notes(self, ctx, customer_id):
        for visit_id, record in self.rows.items():
            visit = self.visits.rows[visit_id]
            if visit.shop_id == ctx.shop_id and visit.customer_id == customer_id:
                self.rows[visit_id] = replace(record, care_note=None, internal_note=None)
        self.journal.append(("clear_record_notes", customer_id))

    async def save(self, ctx, record):
        self.rows[record.visit_id] = record
        self.journal.append(("save_record", record.visit_id, record.version))
        return record

    async def set_hidden(self, ctx, visit_id, hidden_ids):
        self.rows[visit_id] = replace(self.rows[visit_id], media=hide(self.rows[visit_id], hidden_ids))
        self.journal.append(("set_hidden", visit_id, tuple(hidden_ids)))

    async def delete(self, ctx, visit_id):
        self.rows.pop(visit_id, None)
        self.journal.append(("delete_record", visit_id))


class FakeReportRepository(ReportRepository, PublicReportRepository, GuardianReportRepository):
    """visit_reports 스텁 — pg 구현처럼 두 포트를 한 객체가 낸다. 방문의 매장은 visits 스텁에서 본다.

    끊지 않은 줄이 있는 방문에 또 만들면 AssertionError 다 — 인터랙터가 닫기(close_expired)나 끊기를 빠뜨린 것이다.
    살아 있는 링크를 읽은 호출은 reads 에 이름으로 남는다(journal 에는 쓰기만 남긴다).
    """

    def __init__(self, visits: FakeVisits, journal: Journal | None = None) -> None:
        self.visits = visits
        self.journal = journal if journal is not None else Journal()
        self.rows: list[VisitReport] = []
        self.reads: list[str] = []

    def _open(self, ctx, **visit_fields) -> list[VisitReport]:
        """이 매장의, 조건에 맞는 방문에 달린 끊지 않은 줄."""
        return [
            r for r in self.rows
            if r.revoked_at is None and self.visits.rows[r.visit_id].shop_id == ctx.shop_id
            and all(getattr(self.visits.rows[r.visit_id], k) == v for k, v in visit_fields.items())
        ]

    def _revoke(self, reports, now) -> None:
        self.rows = [replace(r, revoked_at=now) if r in reports else r for r in self.rows]

    # --- 보호자용 읽기(GuardianReportRepository) — 끊지 않은 줄(기간은 보지 않는다)과 기록이 있는 방문 ------------

    def _sent(self, ctx, customer_id):
        """records 를 꽂아 두면 기록이 있는 방문만 본다(pg 구현이 visit_records 를 확인하는 것처럼)."""
        records = getattr(self, "records", None)
        found = [
            SentReport(report=r, visit=self.visits.rows[r.visit_id]) for r in self._open(ctx, customer_id=customer_id)
            if records is None or r.visit_id in records.rows
        ]
        return sorted(found, key=lambda s: (s.visit.starts_at, s.visit.id), reverse=True)

    async def list_sent(self, ctx, customer_id, *, pet_id, before, limit):
        found = [
            s for s in self._sent(ctx, customer_id)
            if (pet_id is None or s.visit.pet_id == pet_id)
            and (before is None or (s.visit.starts_at, s.visit.id) < before)
        ]
        return found[:limit]

    async def get_sent(self, ctx, customer_id, report_id):
        return next((s for s in self._sent(ctx, customer_id) if s.report.id == report_id), None)

    async def pet_ids_with_reports(self, ctx, customer_id):
        return sorted({s.visit.pet_id for s in self._sent(ctx, customer_id) if s.visit.pet_id is not None})

    async def get_live(self, ctx, visit_id, now):
        self.reads.append("get_live")
        return next((r for r in self._open(ctx, id=visit_id) if r.is_live(now)), None)

    async def live_visit_ids(self, ctx, visit_ids, now):
        self.reads.append("live_visit_ids")
        return {r.visit_id for r in self._open(ctx) if r.visit_id in visit_ids and r.is_live(now)}

    async def close_expired(self, ctx, visit_id, now):
        self._revoke([r for r in self._open(ctx, id=visit_id) if not r.is_live(now)], now)
        self.journal.append(("close_expired_reports", visit_id))

    async def create(self, ctx, visit_id, public_id, expires_at, now):
        assert all(r.revoked_at is not None for r in self.rows if r.visit_id == visit_id), "끊지 않은 줄이 있다"
        report = VisitReport(
            id=len(self.rows) + 1, visit_id=visit_id, public_id=public_id, expires_at=expires_at, revoked_at=None,
            first_viewed_at=None, created_by_member_id=ctx.member_id, created_at=now)
        self.rows.append(report)
        self.journal.append(("create_report", visit_id))
        return report

    # 모아 보기(⑫) — 질의의 조건은 통합 테스트의 같음 테스트가 본다.
    async def list_media(self, ctx, customer_id, *, pet_id, year, phase, before, limit):
        return []

    async def media_years(self, ctx, customer_id, *, pet_id):
        return []

    async def weights(self, ctx, customer_id, pet_id, limit):
        return []

    async def set_show_review(self, ctx, report_id, show_review):
        self.journal.append(("report_set_show_review", report_id, show_review))

    async def revoke(self, ctx, visit_id, now):
        live = [r for r in self._open(ctx, id=visit_id) if r.is_live(now)]
        self._revoke(live, now)
        self.journal.append(("revoke_report", visit_id))
        return bool(live)

    async def revoke_for_customer(self, ctx, customer_id, now):
        self._revoke(self._open(ctx, customer_id=customer_id), now)
        self.journal.append(("revoke_reports_for_customer", customer_id))

    async def find(self, public_id):
        report = next((r for r in self.rows if r.public_id == public_id), None)
        if report is None:
            return None
        visit = self.visits.rows[report.visit_id]
        return ReportTarget(report=report, shop_id=visit.shop_id, visit=visit)

    async def mark_viewed(self, report_id, now):
        self.rows = [replace(r, first_viewed_at=now) if r.id == report_id and r.first_viewed_at is None else r
                     for r in self.rows]
        self.journal.append(("mark_report_viewed", report_id))


class FakePublicReportLimiter(PublicLimiterPort):
    """공개 조회 횟수 제한 스텁 — allowed 를 False 로 두면 분당 한도를 막고, missed 를 True 로 두면 실패 수 한도가 찬 것으로 친다.

    센 접속 주소가 hits·misses 에, missed_too_much 를 부른 접속 주소가 checked 에 남는다.
    """

    def __init__(self) -> None:
        self.allowed = True
        self.missed = False
        self.hits: list[str] = []
        self.misses: list[str] = []
        self.checked: list[str] = []

    async def allow(self, client):
        self.hits.append(client)
        return self.allowed

    async def note_miss(self, client):
        self.misses.append(client)

    async def missed_too_much(self, client):
        self.checked.append(client)
        return self.missed

    async def allow_write(self, client):
        return self.allowed


class FakeReportSettingsRepository(ReportSettingsRepository):
    """rows 는 매장 ID → 설정. 없는 매장은 기본값이다."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, ReportSettings] = {}

    async def get(self, ctx):
        return self.rows.get(ctx.shop_id, DEFAULT_REPORT_SETTINGS)

    async def update(self, ctx, settings):
        self.journal.append(("update_report_settings", ctx.shop_id))
        self.rows[ctx.shop_id] = settings
        return settings


class FakeRevisitSettingsRepository(RevisitSettingsRepository):
    """rows 는 매장 ID → 다시 올 때 설정. 없는 매장은 처음 값이다."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, RevisitSettings] = {}

    async def get(self, ctx):
        return self.rows.get(ctx.shop_id, DEFAULT_REVISIT_SETTINGS)

    async def update(self, ctx, settings):
        self.journal.append(("update_revisit_settings", ctx.shop_id))
        self.rows[ctx.shop_id] = settings
        return settings


class FakeLibrary(MediaLibraryPort):
    """MediaLibraryPort 스텁 — 실제 구현(media)과 같은 허브 오류를 같은 조건에서 던진다.

    media 는 {media_id: (매장 ID, kind, 준비됨)}. 가져간 것은 attached 에 있다.
    """

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.media: dict[int, tuple[int, str, bool]] = {}
        self.attached: set[int] = set()

    def add(self, media_id, kind="photo", shop_id=1, ready=True, attached=False) -> int:
        self.media[media_id] = (shop_id, kind, ready)
        if attached:
            self.attached.add(media_id)
        return media_id

    async def claim(self, ctx, media_ids):
        self.journal.append(("claim", sorted(media_ids)))
        for media_id in media_ids:
            shop, _, _ = self.media.get(media_id, (None, None, None))
            if shop != ctx.shop_id:
                raise MediaClaimNotFoundError("사진·영상을 찾을 수 없습니다.")
        if any(not self.media[i][2] for i in media_ids):
            raise MediaClaimNotReadyError("아직 올리는 중인 사진·영상입니다.")
        if any(i in self.attached for i in media_ids):
            raise MediaClaimAlreadyAttachedError("이미 다른 기록에 붙은 사진·영상입니다.")
        self.attached |= set(media_ids)
        return {i: self.media[i][1] for i in media_ids}

    async def release(self, ctx, media_ids):
        self.journal.append(("release", sorted(media_ids)))
        self.attached -= set(media_ids)

    async def read_urls(self, ctx, media_ids):
        return {
            i: MediaUrls(media_id=i, kind=self.media[i][1], original_url=f"o/{i}", download_url=f"dl/{i}",
                         display_url=f"d/{i}" if self.media[i][1] == "photo" else None, thumb_url=f"t/{i}",
                         width=3000, height=2000, duration_seconds=None if self.media[i][1] == "photo" else 30)
            for i in media_ids if i in self.media and self.media[i][0] == ctx.shop_id and self.media[i][2]
        }


class FakeShopProfile(ShopProfilePort):
    """ShopProfilePort 스텁 — 매장 ID → ShopProfile 사전. 없는 매장은 None."""

    def __init__(self, shops: dict[int, ShopProfile] | None = None) -> None:
        self.shops = shops if shops is not None else {}

    async def public_profile(self, shop_id):
        return self.shops.get(shop_id)


class FakeEvents(DomainEventPort):
    """DomainEventPort 스텁 — 발행한 이벤트를 published 에 순서대로 모은다. journal 에는 ("publish", 종류, 방문 ID)."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.published: list[VisitEvent] = []
        self.changed: list[tuple[str, int]] = []   # 검색 이벤트(SearchSourceChanged)의 (scope, ref_id)

    async def publish(self, event):
        if isinstance(event, SearchSourceChanged):
            self.changed.append((event.scope, event.ref_id))
            return
        self.published.append(event)
        self.journal.append(("publish", type(event).__name__, event.visit_id))


class FakeSalesGoalRepository(SalesGoalRepository):
    """rows 는 매장 ID → 월 목표. 없는 매장은 목표가 없다."""

    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, int | None] = {}

    async def get(self, ctx):
        return self.rows.get(ctx.shop_id)

    async def put(self, ctx, monthly_amount):
        self.journal.append(("put_sales_goal", ctx.shop_id))
        self.rows[ctx.shop_id] = monthly_amount
        return monthly_amount


class FakeSalesRepository(SalesRepository):
    """SalesRepository 스텁 — 기간(start, until)마다 넣어 둔 값을 돌려준다. 넣지 않은 기간은 비어 있다.

    calls 에 부른 메서드 이름이 차례로 남는다(질의 수를 고정하는 테스트가 본다).
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.totals_by: dict[tuple, SalesTotals] = {}
        self.days_by: dict[tuple, list[DaySales]] = {}
        self.payments_by: dict[tuple, dict] = {}
        self.menus_by: dict[tuple, list[MenuSales]] = {}
        self.pets_by: dict[tuple, list[PetVisits]] = {}
        self.reports_by: dict[tuple, tuple[int, int]] = {}
        self.remaining = RemainingBookings(count=0, expected_amount=None)
        self.remaining_args: tuple | None = None
        self.visit_rows: list[SalesVisitRow] = []
        self.visit_args: tuple | None = None

    async def totals(self, ctx, start, until):
        self.calls.append("totals")
        return self.totals_by.get((start, until), SalesTotals(0, 0, 0, 0, 0, 0))

    async def by_day(self, ctx, start, until):
        self.calls.append("by_day")
        return self.days_by.get((start, until), [])

    async def by_payment(self, ctx, start, until):
        self.calls.append("by_payment")
        return self.payments_by.get((start, until), {})

    async def by_menu(self, ctx, start, until):
        self.calls.append("by_menu")
        return self.menus_by.get((start, until), [])

    async def pets(self, ctx, start, until):
        self.calls.append("pets")
        return self.pets_by.get((start, until), [])

    async def remaining_reserved(self, ctx, since, until):
        self.calls.append("remaining_reserved")
        self.remaining_args = (since, until)
        return self.remaining

    async def report_counts(self, ctx, start, until):
        self.calls.append("report_counts")
        return self.reports_by.get((start, until), (0, 0))

    async def list_visits(self, ctx, start, until, kind, menu_id, before, limit):
        self.calls.append("list_visits")
        self.visit_args = (start, until, kind, menu_id, before, limit)
        rows = [r for r in self.visit_rows if before is None or (r.starts_at, r.visit_id) < before]
        return rows[:limit]



class FakeChecks(VisitCheckRepository):
    """확인할 것의 방문 쪽 사실 스텁 — 완료 방문(반려동물 ID → 시작 시각들)과 노쇼(고객 ID → 시작 시각들).

    실제 저장소와 같은 계약으로 답하고, 메서드마다 받은 물음을 calls 에 남긴다(질의 수를 고정하는 테스트).
    """

    def __init__(self) -> None:
        self.completed: dict[int, list] = {}
        self.no_show_starts: dict[int, list] = {}
        self.calls: list[tuple[str, int]] = []

    async def last_completed(self, ctx, asks):
        self.calls.append(("last_completed", len(asks)))
        return {
            ask.key: max((s for s in self.completed.get(ask.pet_id, ()) if s < ask.before), default=None)
            for ask in asks
        }

    async def no_shows(self, ctx, asks):
        self.calls.append(("no_shows", len(asks)))
        return {
            ask.key: sum(1 for s in self.no_show_starts.get(ask.customer_id, ()) if ask.since <= s < ask.until)
            for ask in asks
        }
