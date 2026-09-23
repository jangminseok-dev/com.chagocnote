"""visit 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다."""
from __future__ import annotations

from dataclasses import replace

from visit.domain.entities.menu import Menu
from visit.domain.errors import MenuNameTakenError, MenuNotFoundError
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
